import functools
from copy import copy
from datetime import datetime, date
from decimal import Decimal

from flask import (
    render_template, request, session, g, redirect, url_for, abort, 
    flash, send_file, escape, jsonify)

from cfmi.billing import app, cfmiauth
from cfmi.billing.models import User, Project, Session, Invoice, Problem

model_map = {'user': User, 'project': Project, 'session': Session,
             'invoice': Invoice, 'problem': Problem}

# Utility functions

def flatten(obj, attrib_filter=None):
    goodstuff = copy(obj.__dict__)
    if attrib_filter:
        for key in obj.__dict__:
            if not key in attrib_filter:
                del goodstuff[key]
    for key, value in goodstuff.iteritems():
        if isinstance(value, datetime):
            goodstuff[key]=value.strftime("%m/%d/%Y %H:%M")
        if isinstance(value, date):
            goodstuff[key]=value.strftime("%m/%d/%Y")
        if isinstance(value, Decimal):
            goodstuff[key]=float(value)
    if '_sa_instance_state' in goodstuff:
        del goodstuff['_sa_instance_state']
    return goodstuff

def safe_eval(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except NameError:
            ## Incorrect model name attempted
            abort(403)
        except AttributeError:
            ## existing non-model class access attempted
            abort(403)
    return wrapper

# Views

@app.route('/api/db/<model>')
@cfmiauth.superuser_only
@safe_eval
def model_summary(model=None):
    object_list = eval(model.capitalize()).query.all()
    flat_list = [flatten(object) for object in object_list]
    return jsonify({'model': model, 'object_list': flat_list})

@app.route('/api/activePI')
@cfmiauth.superuser_only
def admin_list_pi():
    active_projects = Project.query.filter(Project.is_active==True)
    pi_list = []
    for project in active_projects:
        if not project.pi in pi_list:
            pi_list.append(project.pi)
    flat_list = [flatten(pi, attrib_filter=['name','username','id']) for pi in pi_list]
    return jsonify({'name':"active_pis", 'object_list': flat_list})
    
@app.route('/api/db/<model>/<int:id>')
@safe_eval
def model_instance(model, id):
    inst = eval(model.capitalize()).query.get(id)
    if not inst:
        abort(404)
    return jsonify(flatten(inst))

@app.route('/api/user')
@cfmiauth.login_required
def user_info():
    return jsonify(flatten(g.user))

@app.route('/api/projects')
@cfmiauth.login_required
def user_project_list():
    return jsonify({
            "projects": [flatten(proj) for proj in g.user.get_projects()]})

@app.route('/api/projects/<int:project_id>')
@cfmiauth.authorized_users_only
def user_project_detail(project_id):
    proj = Project.query.get(project_id)
    if not proj:
        abort(404)
    today = date.today()
    year = today.year
    month = today.month
    if 'year' in request.args:
        year = int(request.args['year'])
    if 'month' in request.args:
        month = int(request.args['month'])
    flatproj = flatten(proj)
    if month > 0 and month <= 12:
        flatproj['sessions'] = [
            flatten(session) for session in proj.invoice_scans(year, month)]
    else: flatproj['sessions'] = []
    return jsonify(flatproj)
