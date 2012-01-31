import functools
from datetime import datetime, date

from flask import (render_template, request, session, g, redirect,
                   abort, jsonify, current_app, Blueprint, url_for)

from cfmi.database.newsite import (User, Project, Session, Invoice, Problem,
                                   Subject)
from cfmi.database.dicom import Series, DicomSubject
from cfmi.auth import (superuser_only, login_required)

from cfmi import cache, db
from cfmi.utils import flatten

rest = Blueprint('rest_api', __name__)

API_MODEL_MAP = {'user': User, 
                 'project': Project,
                 'session': Session, 
                 'invoice': Invoice,
                 'problem': Problem,
                 'series': Series,
                 'subject': Subject,
                 'dicomsubject': DicomSubject}

STRING_KEYED_MODELS = [Series, DicomSubject]

USER_CREATABLE_MODELS = [Session, Subject, Project, Problem]
USER_EDITABLE_MODELS = [User, Project, Problem, Subject]
USER_DEL_MODELS = [Problem]

## Flask Hooks
@rest.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])

## API Authentication
def api_auth(instance):
    if g.user.is_superuser():
        return True
    ## Series-like object (converted to DicomSubject)
    if hasattr(instance, 'study_id'):
        instance = instance.subject
    ## DicomSubject-like objects (converted to Subject)
    if hasattr(instance, 'get_series'):
        instance = Subject.query.filter_by(name=instance.subject.name)
    ## Subject, Invoice, Session-like objects
    if hasattr(instance, 'project'):
        instance = instance.project
    ## Problem-like objects
    if hasattr(instance, 'session'):
        instance = instance.session.project
    ## User-like objects
    if hasattr(instance, 'username'):
        if instance.username == g.user.username:
            # User accessing own user object
            return True
        for user_list in [project.users for project in g.user.pi_projects]:
            # User accessing user object of user working on their
            # project
            if instance in user_list:
                return True
    ## Project-like objects
    if hasattr(instance, 'pi') and hasattr(instance, 'users'):
        if instance.pi == g.user:
            return True
        if g.user in instance.users:
            return True
    return False

## Views

@rest.route('/db/<model>/<pk>', methods=['GET', 'PUT', 'DELETE'])
def model_instance(model, pk):
    Model = API_MODEL_MAP[model]
    if not Model in STRING_KEYED_MODELS: 
        id = int(pk)
    inst = API_MODEL_MAP[model].query.get(pk)
    if not inst:
        abort(404)
    if not api_auth(inst):
        abort(403)
    if request.method == 'DELETE':
        if not g.user.is_superuser(): 
            if not Model in USER_DEL_MODELS:
                abort(403)
        db.session.delete(inst)
        db.session.commit()
    if request.method == 'PUT':
        if not inst:
            abort(404)
        if not api_auth(inst):
            abort(403)
        if not g.user.is_superuser():
            if not Model in USER_EDITABLE_MODELS:
                abort(403)
        for key, value in request.json.iteritems():
            inst.__setattr__(key, value)
        db.session.commit()
    return jsonify(flatten(inst))

@rest.route('/db/<model>', methods=['GET', 'POST'])
def model_summary(model):
    Model = API_MODEL_MAP[model]
    if request.method == 'POST':
        inst = Model()
        for key, value in request.json.iteritems():
            inst.__setattr__(key, value)
        if not g.user.is_superuser():
            if not Model in USER_CREATABLE_MODELS:
                abort(403)
        if not api_auth(inst):
            abort(403)
        db.session.add(inst)
        db.session.commit()
        return redirect(url_for('.model_instance', model=model, pk=inst.id))

    inst_list = filter(api_auth, Model.query.all())
    for inst in inst_list:
        inst.url = '/'+'/'.join(url_for('.model_instance', model=model, pk=inst.id).split('/')[3:])
    flat_list = [flatten(inst) for inst in inst_list]
    return jsonify({'model': model, 'object_list': flat_list})

@rest.route('/user')
@login_required
def user_info():
    return jsonify(flatten(g.user))
