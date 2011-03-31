import functools
import smtplib
from copy import copy
from datetime import datetime, date
from decimal import Decimal
from email.mime.text import MIMEText

from flask import (
    render_template, request, session, g, redirect, url_for, abort, 
    flash, send_file, escape, jsonify, current_app, Module)

from cfmi.billing.models import User, Project, Session, Invoice, Problem, db_session
from cfmi.common.auth.decorators import (superuser_only, login_required,
                                         authorized_users_only)

from cfmi.billing.utils import limit_month, active_projects
from cfmi.billing.settings import cache

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
    for key, value in obj.__dict__.iteritems():
        if isinstance(value, (User, Project, Session, Invoice, Problem)):
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

@api.route('/batch/gen_invoices')
@superuser_only
def gen_invoices():
    if not 'year' in request.args and 'month' in request.args:
        abort(403)
    year = int(request.args['year'])
    month = int(request.args['month'])
    invoice_date = date(year, month, 1)
    projs = active_projects(year, month)
    count = 0
    for project in projs:
        if not len(Invoice.query.filter(
                Invoice.project==project).filter(
                Invoice.date==invoice_date).all()):
            # If the invoice exists already, don't bother
            inv = Invoice()
            inv.project = project
            inv.date = invoice_date
            db_session.add(inv)
            db_session.commit()
            count += 1
    return jsonify(new_invoices=count, status="Success")

@api.route('/db/invoice/<int:invoice_id>/notify')
@superuser_only
def invoice_send_email(invoice_id):
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        abort(404)
    msg = MIMEText(render_template('email.txt', invoice=invoice))
    msg['Subject'] = "CFMI Invoice: {0}".format(invoice.date.strftime("%b %Y"))
    msg['From'] = 'billing@cfmi.georgetown.edu'
    msg['Reply-to'] = 'billing@cfmi.georgetown.edu'
    msg['To'] = invoice.project.pi.email
    #msg['To'] = 'sn253@georgetown.edu'
    s = smtplib.SMTP()
    s.connect('localhost')
    s.sendmail('billing@cfmi.georgetown.edu', ['sn253@georgetown.edu'], msg.as_string())
    s.quit()
    invoice.sent = True
    db_session.commit()
    print invoice
    return jsonify(flatten(invoice))

@api.route('/batch/update_stats')
@superuser_only
def update_stats():
    #cache.delete_memoized(['month_total', 'fical_year'])
    return jsonify({})

@api.route('/batch/spoof/<username>')
@superuser_only
def spoof_user(username):
    user = User.query.filter(User.username==username).first()
    if not user:
        abort(404)
    session['user_id'] = user.id
    return jsonify({})
    
@api.route('/db/<model>', methods=['GET', 'POST'])
@superuser_only
#@safe_eval
def model_summary(model):
    if request.method == 'POST':
        inst = eval(model.capitalize())()
        for key, value in request.json.iteritems():
            inst.__setattr__(key, value)
        db_session.add(inst)
        db_session.commit()
        return model_instance(model, inst.id) 

    object_list = eval(model.capitalize()).query.all()
    flat_list = [flatten(object) for object in object_list]
    return jsonify({'model': model, 'object_list': flat_list})

@api.route('/db/<model>/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@superuser_only
#@safe_eval
def model_instance(model, id):
    inst = eval(model.capitalize()).query.get(id)
    if request.method == 'DELETE':
        if not inst:
            abort(404)
        db_session.delete(inst)
        db_session.commit()
        return jsonify(flatten(inst))
    if request.method == 'PUT':
        if not inst:
            abort(404)
        for key, value in request.json.iteritems():
            inst.__setattr__(key, value)
        db_session.commit()
    if not inst:
        abort(404)
    print inst
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
