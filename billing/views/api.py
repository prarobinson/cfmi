import functools
from copy import copy
from datetime import datetime, date
from decimal import Decimal

from flask import (
    render_template, request, session, g, redirect, url_for, abort, 
    flash, send_file, escape, jsonify, current_app, Module)

from cfmi.billing.models import User, Project, Session, Invoice, Problem
from cfmi.common.auth.decorators import (superuser_only, login_required,
                                         authorized_users_only)

from cfmi.billing.utils import limit_month

api = Module(__name__)

## Flask Hooks
@api.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])

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
    def wrapier(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except NameError:
            ## Incorrect model name attempted
            abort(403)
        except AttributeError:
            ## existing non-model class access attempted
            abort(403)
    return wrapier

# Views

@api.route('/db/<model>')
@superuser_only
@safe_eval
def model_summary(model=None):
    object_list = eval(model.capitalize()).query.all()
    flat_list = [flatten(object) for object in object_list]
    return jsonify({'model': model, 'object_list': flat_list})

@api.route('/activePI')
@superuser_only
def admin_list_pi():
    active_projects = Project.query.filter(Project.is_active==True)
    if 'year' in request.args and 'month' in request.args:
        active_projects = limit_month(active_projects,
            int(request.args['year']), 
            int(request.args['month']))
    pi_list = []
    for project in active_projects:
        if not project.pi in pi_list:
            pi_list.append(project.pi)
    flat_list = [flatten(pi, attrib_filter=['name','username','id']) for pi in pi_list]
    return jsonify({'name':"active_pis", 'object_list': flat_list})

# @api.route('/activePI/<user_id>')
# @superuser_only
# def admin_list_pi_projects(user_id):
#     pi = User.query.get(user_id)
#     active_pi_projects = []
#     for proj in pi.pi_projects:
#         if len(proj.invoice_scans(
#                 int(request.args['year']), int(request.args['month']))):
#             proj.shortname = proj.shortname()
#             active_pi_projects.append(proj)
#     flat_list = [
#         flatten(
#             proj, attrib_filter=[
#                 'shortname', 'id']) for proj in active_pi_projects]
#     return jsonify({'piuname':pi.username, 'object_list': flat_list})
    
    
@api.route('/db/<model>/<int:id>')
@login_required
@safe_eval
def model_instance(model, id):
    inst = eval(model.capitalize()).query.get(id)
    if not inst:
        abort(404)
    return jsonify(flatten(inst))

@api.route('/user')
@login_required
def user_info():
    return jsonify(flatten(g.user))

@api.route('/projects')
@login_required
def user_project_list():
    return jsonify({
            "projects": [flatten(proj) for proj in g.user.get_projects()]})

@api.route('/projects/<int:project_id>')
@authorized_users_only
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
