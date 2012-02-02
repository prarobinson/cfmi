import functools
import inspect
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

## Routing for the api (also ACL)
API_MODEL_MAP = {'user': User, 
                 'project': Project,
                 'session': Session, 
                 'invoice': Invoice,
                 'problem': Problem,
                 'series': Series,
                 'subject': Subject,
                 'dicomsubject': DicomSubject
}

## Allows us to lookup url from a Class or instance
API_REVERSE_MAP = dict((API_MODEL_MAP[k], k) for k in API_MODEL_MAP)

## Maps relation names that don't match the model name while avoiding
## redundant urls for the models
API_MODEL_EQ = {'pi': 'user'}

## Used to decide when not to convert to int for fetching by pk
STRING_KEYED_MODELS = [Series, DicomSubject]

## No summary allowed on these Models due to performance concerns.
NO_SUMMARY_ALLOWED = [Session, Series, DicomSubject]

## Authorization
USER_CREATABLE_MODELS = [Session, Subject, Project, Problem]
USER_EDITABLE_MODELS = [User, Project, Problem, Subject]
USER_DEL_MODELS = [Problem]

## Flask Hooks
@rest.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])

# Utility Routines

def instance_to_url(modstr_or_inst, pk=None):
    if pk == None:
        model = API_REVERSE_MAP[modstr_or_inst.__class__]
        pk = modstr_or_inst.id
    else:
        model = modstr_or_inst
    url = url_for('.model_instance',
                         model=model, pk=pk)
    if url.startswith('http://'):
        ## url_for returns relative url for the first mountpoint of
        ## the blueprint and absolute url of the first mountpoint for
        ## subsequent mounts. We're using this for ajax so we need the
        ## api mounted at all subdomains... truncating the absolute
        ## url works here but is ugly.
        url = '/'+'/'.join(url.split('/')[3:])
    return url

def flatten(obj, attrib_filter=None):  
    extra = [(thing, getattr(obj, thing)) for thing in dir(obj)]
    for key, value in extra:
        if not key in obj.__dict__ and isinstance(value, (u''.__class__, [].__class__)):
            obj.__dict__[key] = value
    goodstuff = {}
    for key, value in obj.__dict__.iteritems():
        if key is 'id':
            ## Expand id field to url
            key = 'url'
            if attrib_filter and not key in attrib_filter:
                    continue
            value = instance_to_url(obj)
        if key.endswith('_id'):
            model = key[:-3]
            if model in API_MODEL_EQ:
                model = API_MODEL_EQ[model]
            if model in API_MODEL_MAP:
                ## We know about this relation, expand to related url
                key = model
                if attrib_filter and not key in attrib_filter:
                    continue
                value = instance_to_url(model, pk=value)
        if value.__class__ in API_MODEL_MAP.values():
            ## The field is a foreign keyed object, replace with url
            #goodstuff[key] = instance_to_url(value)
            value = instance_to_url(value)
        if isinstance(value, [].__class__):
            value = [instance_to_url(subitem) for subitem in value]
            #goodstuff[key] = [instance_to_url(subitem) for subitem in value]
        if attrib_filter and not key in attrib_filter:
            continue
        goodstuff[key] = value
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
    if not model in API_MODEL_MAP:
        abort(403)
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
    #if isinstance(inst, Subject):
    #    dicom_subject = DicomSubject.query.filter_by(name=inst.name).first()
    #    inst.data = Series.query.filter_by(subject=dicom_subject).all()
    #if isinstance(inst, Session):
    #    dicom_subject = DicomSubject.query.filter_by(name=inst.subject.name).first()
    #    inst.data = Series.query.filter_by(subject=dicom_subject).filter_by(date=inst.start).all()
    return jsonify(flatten(inst))

@rest.route('/db/<model>', methods=['GET', 'POST'])
def model_summary(model):
    if not model in API_MODEL_MAP:
        abort(403)
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
    if Model in NO_SUMMARY_ALLOWED:
        abort(403)
    inst_list = filter(api_auth, Model.query.all())
    flat_list = [flatten(inst, attrib_filter=['url']) for inst in inst_list]
    return jsonify({'model': model, 'count': len(flat_list), 'object_list': flat_list})

@rest.route('/user')
@login_required
def user_info():
    return jsonify(flatten(g.user, attrib_filter=['name','url','username']))
