import functools
import smtplib
from datetime import datetime, date
from email.mime.text import MIMEText

from flask import (render_template, request, session, g, redirect,
                   abort, flash, send_file, escape, jsonify, current_app,
                   Blueprint)

from cfmi.billing.models import User, Project, Session, Invoice, Problem
from cfmi.auth import (superuser_only, login_required,
                       authorized_users_only)

from cfmi.billing.utils import limit_month, active_projects
from cfmi import cache, db
from cfmi.utils import flatten

api = Blueprint('billing_api', __name__, static_folder='../static',
                template_folder='../templates')

## Flask Hooks
@api.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])

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
            db.session.add(inv)
            db.session.commit()
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
    msg['Reply-to'] = 'cfmiadmin@georgetown.edu'
    msg['To'] = invoice.project.pi.email
    recip = ['sn253@georgetown.edu']
    if not current_app.config['TESTING']:
        recip += [invoice.project.pi.email, 'cfmiadmin@georgetown.edu']
        if invoice.project.email and invoice.project.email is not invoice.project.pi.email:
            msg['Cc'] = invoice.project.email
            recip.append(invoice.project.email)
    s = smtplib.SMTP()
    s.connect('localhost')
    s.sendmail('billing@cfmi.georgetown.edu',
               recip,
               msg.as_string())
    s.quit()
    invoice.sent = True
    db.session.commit()
    return model_instance("invoice", invoice_id)

def problem_send_email(session_id, problem, duration):
    scan = Session.query.get(session_id)
    msg = MIMEText(render_template('email_problem.txt', session_id=session_id,
                                   problem=problem.data, duration=duration.data))
    msg['Subject'] = "Session problem report: {0}".format(session_id)
    msg['From'] = 'billing@cfmi.georgetown.edu'
    msg['Reply-to'] = g.user.email if g.user.email else scan.project.email
    msg['To'] = 'cfmiadmin@georgetown.edu'
    recip = ['sn253@georgetown.edu']
    if not current_app.config['TESTING']:
        recip += ['cfmiadmin@georgetown.edu']
    if g.user.email:
        msg['Cc'] = g.user.email
        recip.append(g.user.email)
    s = smtplib.SMTP()
    s.connect('localhost')
    s.sendmail('billing@cfmi.georgetown.edu', recip,
               msg.as_string())
    s.quit()

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

@api.route('/projects')
@login_required
def user_project_list():
    return jsonify({
            "projects": [flatten(proj) for proj in g.user.get_projects()]})
