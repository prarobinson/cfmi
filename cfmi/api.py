import functools
from datetime import datetime, date
from copy import copy
from decimal import Decimal

from flask import (render_template, request, session, g, redirect,
                   abort, jsonify, current_app, Blueprint, url_for)

from cfmi.database.newsite import (User, Project, Session, Invoice, Problem,
                                   Subject)
from cfmi.database.dicom import Series, DicomSubject
from cfmi.auth import (superuser_only, login_required)

from cfmi import cache, db

rest = Blueprint('rest_api', __name__)

API_MODEL_MAP = {'user': User, 
                 'project': Project,
                 'session': Session, 
                 'invoice': Invoice,
                 'problem': Problem,
                 'series': Series,
                 'subject': Subject,
                 'dicomsubject': DicomSubject}

API_REVERSE_MAP = dict((API_MODEL_MAP[k], k) for k in API_MODEL_MAP)

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

## JSON Serializer

def instance_to_url(instance):
    model = API_REVERSE_MAP[instance.__class__]
    return '/'+'/'.join(url_for('.model_instance',
                         model=model, pk=instance.id).split('/')[3:])

def flatten(obj, attrib_filter=None):
    goodstuff = copy(obj.__dict__)
    if attrib_filter:
        for key in obj.__dict__:
            ## If there is a filter, remove everything else
            if not key in attrib_filter:
                del goodstuff[key]
    for key, value in obj.__dict__.iteritems():
        if key is 'id':
            ## Expand id field to url
            model = API_REVERSE_MAP[obj.__class__]
            goodstuff['url'] = '/'+'/'.join(
                url_for('.model_instance',
                        model=model, pk=value).split('/')[3:])
            #del goodstuff[key]
            continue
        if key.endswith('_id'):
            model = key[:-3]
            if model in API_MODEL_MAP.keys():
                ## We know about this relation, expand to related url
                goodstuff[model] = '/'+'/'.join(
                    url_for('.model_instance',
                            model=model, pk=value).split('/')[3:])
                del goodstuff[key]
                continue
        if value.__class__ in API_MODEL_MAP.values():
            ## The field is a foreign keyed object, replace with url
            goodstuff[key] = instance_to_url(value)
            continue
        if isinstance(value, [].__class__):
            goodstuff[key] = [instance_to_url(subitem) for subitem in value]
            continue
    for key, value in goodstuff.iteritems():
        if isinstance(value, datetime):
            goodstuff[key]=value.strftime("%m/%d/%Y %H:%M")
            continue
        if isinstance(value, date):
            goodstuff[key]=value.strftime("%m/%d/%Y")
            continue
        if isinstance(value, Decimal):
            goodstuff[key]=float(value)
            continue
    if '_sa_instance_state' in goodstuff:
        del goodstuff['_sa_instance_state']
    return goodstuff

## API Authentication
def api_auth(instance):
    if g.user.is_superuser():
        return True
    ## Series-like object (converted to DicomSubject)
    if hasattr(instance, 'study_id'):
        instance = instance.subject
    ## DicomSubject-like objects (converted to Subject)
    if isinstance(instance, DicomSubject):
        if instance.name in g.user.get_subjects():
            return True
    ## Subject, Invoice, Session-like objects
    if hasattr(instance, 'project'):
        instance = instance.project
    ## Problem-like objects
    if hasattr(instance, 'session_id'):
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
    if isinstance(inst, Subject):
        dicom_subject = DicomSubject.query.filter_by(name=inst.name).first()
        inst.data = Series.query.filter_by(subject=dicom_subject).all()
    if isinstance(inst, Session):
        dicom_subject = DicomSubject.query.filter_by(name=inst.subject.name).first()
        inst.data = Series.query.filter_by(subject=dicom_subject).filter_by(date=inst.start).all()
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
    flat_list = [flatten(inst) for inst in inst_list]
    return jsonify({'model': model, 'count': len(flat_list), 'object_list': flat_list})

@rest.route('/user')
@login_required
def user_info():
    return jsonify(flatten(g.user))
