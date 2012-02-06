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

## No summary allowed on these Models because the dicom database is
## slow. Series are most usefully accessed via their relation to
## Session objects and no one really needst to access DicomSubject.
NO_SUMMARY_ALLOWED = [Series, DicomSubject]

## Authorization
USER_CREATABLE_MODELS = [Session, Subject, Project, Problem]
USER_EDITABLE_MODELS = [User, Project, Problem] # How to avoid price change?
USER_DEL_MODELS = [Problem]

# We cannot, cannot, CANNOT modify the DICOM database. This is
# enforced by database perms, but lets not think about this, eh?
IMMUTABLE_MODELS = [Series, DicomSubject]

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
        ## urlfor_ returns relative url for the first mountpoint of
        ## the blueprint and absolute url of the first mountpoint for
        ## subsequent mounts. We're using this for ajax so we need the
        ## api mounted at all subdomains... truncating the absolute
        ## url works here but is ugly.
        url = '/'+'/'.join(url.split('/')[3:])
    return url

def url_to_instance(url):
    parts = url.split('/')
    Model = None
    idx = None
    for part in parts:
        if part in API_MODEL_MAP:
            idx = parts.index(part)
            Model = API_MODEL_MAP[part]
            break
    pk = parts[idx+1] if idx else None
    inst = Model.query.get(pk) if Model and pk else None
    return inst

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
            value = instance_to_url(value)
        if isinstance(value, [].__class__):
            value = '/'.join([instance_to_url(API_REVERSE_MAP[obj.__class__],
                            pk=obj.id), key])
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
def api_auth(instance, mode='read'):
    ## Check if the Model is read-only
    if mode is not 'read':
        if instance.__class__ in IMMUTABLE_MODELS:
            return False
    if g.user.is_superuser():
        return True
    ## Check if this operation is allowed by users
    if mode == 'create' and Model not in USER_CREATABLE_MODELS or \
            mode == 'edit' and Model not in USER_EDITABLE_MODELS or \
            mode == 'delete' and Model not in USER_DEL_MODELS:
        return False
    ### Below are the specific rules for user access, they are
    ### designed to rely on duck-typing to 'guess-out' how to auth new
    ### objects. Best to check these rules when adding / designing new
    ### classes

    ## Series-like object (converted to DicomSubject)
    if hasattr(instance, 'study_id'):
        instance = instance.subject
    ## DicomSubject-like objects (converted to Session)
    if isinstance(instance, DicomSubject):
        if not len(instance.series) or not instance.series[0].date:
            # No data (invalid subj) or no date to auth via session
            return False
        first_series = instance.series[0]
        instance = Session.query.filter(
            first_series.date>=Session.start).filter(first_series.date<=Session.end).first()
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
@rest.route('/db/<model>/<pk>/<relation>', methods=['GET', 'POST'])
@login_required
def relation_summary(model, pk, relation):
    if not g.user: abort(403)
    if not model in API_MODEL_MAP:
        abort(403)
    Model = API_MODEL_MAP[model]
    if not Model in STRING_KEYED_MODELS:
        pk = int(pk)
    inst = API_MODEL_MAP[model].query.get(pk)
    if not inst:
        abort(404)
    if request.method == 'POST':
        relation_field_string = relation = '_id'
        request.json[relation_field_string] = inst.id
        return model_summary(model)
    if not api_auth(inst):
        abort(403)
    if hasattr(inst, relation):
        if isinstance(getattr(inst, relation), [].__class__):
            flat_list = [instance_to_url(inst) for inst in getattr(inst, relation)]
            return jsonify({'count': len(flat_list),
                            'object_list': flat_list})
    return abort(404)

@rest.route('/db/<model>/<pk>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def model_instance(model, pk):
    if not g.user: abort(403)
    if not model in API_MODEL_MAP:
        abort(403)
    Model = API_MODEL_MAP[model]
    if not Model in STRING_KEYED_MODELS: 
        pk = int(pk)
    inst = API_MODEL_MAP[model].query.get(pk)
    if not inst:
        abort(404)
    if not api_auth(inst):
        abort(403)
    if request.method == 'DELETE':
        if not api_auth(inst, mode='delete'):
            abort(403)
        db.session.delete(inst)
        db.session.commit()
    if request.method == 'PUT':
        if not api_auth(inst, mode='edit'):
            abort(403)
        for key, value in request.json.iteritems():
            inst.__setattr__(key, value)
        db.session.commit()
    return jsonify(flatten(inst))

@rest.route('/db/<model>', methods=['GET', 'POST'])
@login_required
def model_summary(model):
    if not g.user: abort(403)
    if not model in API_MODEL_MAP:
        abort(403)
    Model = API_MODEL_MAP[model]
    if request.method == 'POST':
        inst = Model()
        for key, value in request.json.iteritems():
            inst.__setattr__(key, value)
        if not api_auth(inst, mode='create'):
            abort(403)
        db.session.add(inst)
        db.session.commit()
        return redirect(instance_to_url(model, pk=inst.id))
    if Model in NO_SUMMARY_ALLOWED:
        abort(403)
    query = Model.query
    for arg in request.args:
        if hasattr(Model, arg):
            query = Model.query.filter(getattr(Model, arg)==request.args[arg])
        else:
            ## They've filtered on a non-existant attr, return no hits
            return jsonify({'model': model, 'count': 0, 'object_list': []})
    inst_list = filter(api_auth, query.all())
    flat_list = [instance_to_url(inst) for inst in inst_list]
    return jsonify({'model': model, 'count': len(flat_list), 'object_list': flat_list})

@rest.route('/user')
@login_required
def user_info():
    return jsonify(flatten(g.user, attrib_filter=['name','url','username']))
