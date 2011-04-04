from datetime import timedelta, date
from subprocess import call

from flask import (
    render_template, request, session, g, redirect, url_for, abort, 
    flash, send_file, escape, current_app, Module)

from cfmi.billing.settings import cache
from cfmi.billing.models import (User, Project, Session, Problem, Invoice, 
                                 Subject, db_session)
from cfmi.common.auth.decorators import (superuser_only, login_required,
                                         authorized_users_only)

from cfmi.billing.utils import (
    fiscal_year, total_last_month, limit_month, gchart_ytd_url, active_projects)
from cfmi.billing.views.api import invoice_send_email

from formalchemy import FieldSet
from cfmi.billing.forms import ROSessionForm, SessionForm, ProblemForm, ProblemRequestForm

frontend = Module(__name__)

## Views

@frontend.route('/')
@login_required
def index():
    if not g.user.is_superuser():
        return redirect(url_for("user_portal"))
    return render_template('index.html')

@frontend.route('/user/')
@login_required
def user_portal():
    today = date.today()
    recent = []
    unpaid = []
    for project in g.user.projects:
        # A kludgy way to get all the user's scans from the last month
        recent += project.invoice_scans(today.year, today.month)
        unpaid += Invoice.query.filter(
            Invoice.project==project).filter(Invoice.reconciled==False).all()
    return render_template('user.html', recent=recent, unpaid=unpaid)

@frontend.route('/reconcile/')
@superuser_only
def reconcile():
    outstanding = Invoice.query.filter(Invoice.reconciled==False).order_by(Invoice.date)
    return render_template('reconcile.html', invoice_list=outstanding)

@frontend.route('/invoice/<int:invoice_id>/')
@authorized_users_only
def invoice_view(invoice_id):
    inv = Invoice.query.get(invoice_id)
    if not inv:
        abort(404)
    return render_template('invoice.html', invoice=inv)

@frontend.route('/invoice/<int:id>/delete')
@superuser_only
def invoice_delete(id):
    inv = Invoice.query.get(id)
    if not inv:
        abort(404)
    db_session.delete(inv)
    db_session.commit()
    return redirect(url_for('reconcile'))

@frontend.route('/invoice/<int:id>/paid')
@superuser_only
def invoice_paid(id):
    inv = Invoice.query.get(id)
    if not inv:
        abort(404)
    inv.reconciled = True
    db_session.commit()
    return redirect(url_for('reconcile'))

@frontend.route('/invoice/<int:invoice_id>/notify')
@superuser_only
def invoice_notify(invoice_id):
    inv = Invoice.query.get(invoice_id)
    if not inv:
        abort(404)
    invoice_send_email(invoice_id)
    return redirect(url_for('reconcile'))

@frontend.route('/stats/')
@login_required
def statistics():
    return render_template(
        'stats.html', ytd=fiscal_year(), lastyear=fiscal_year(2010), 
        lastmonth=total_last_month(), gchart_ytd_url=gchart_ytd_url(), 
        sessions=len(Session.query.all()), subjects=len(Subject.query.all()))

@frontend.route('/batch/')
@superuser_only
def batch():
    return render_template('batch.html')

@frontend.route('/batch/report')
@superuser_only
def batch_report():
    if not 'year' in request.args and 'month' in request.args:
        abort(404)
    year = int(request.args['year'])
    month = int(request.args['month'])
    projects = active_projects(year, month)
    return render_template('report.html', projects=projects, date=date(year, month, 1) )

@frontend.route('/invoice/<invoice_id>')
@authorized_users_only
def invoice(id):
    inv = Invoice.query.get(invoice_id)
    if not inv:
        abort(404)
    return inv.render()

@frontend.route('/<pi_uname>/<int:year>/<int:month>/')
@authorized_users_only
def pi_month_view(pi_uname, year, month):
    pi = User.query.filter(User.username==pi_uname).first()
    if not pi:
        abort(404)
    if 'format' in request.args:
        if request.args['format'] == 'tex':
            return render_template('invoice.tex', pi=pi,
                                   date=date(year,month,1))
        if request.args['format'] == 'pdf':
            tex = render_template('invoice.tex', pi=pi,
                                  date=date(year,month,1))
            path = '/tmp/invoice-%s_%s-%s' % (pi_uname, month, year)
            tmpfile = open(path+'.tex', 'w')
            tmpfile.write(tex)
            tmpfile.close()
            r = call(['pdflatex', path+'.tex'], cwd='/tmp/')
            path = path+'.pdf'
            return send_file(path, as_attachment=True)

    mindate = date(year, month, 1)
    
    query = Session.query.join(Project).filter(
        Project.pi==pi)
    scans = limit_month(query, year, month)
    
    total = sum(float(scan.cost()) for scan in scans)
    total = "{0:.2f}".format(total)
    return render_template('pi_month_view.html', pi=pi, 
                           date=mindate, total=total)

@frontend.route('/session/<int:session_id>/', methods=['GET', 'POST'])
@authorized_users_only
def edit_session(session_id):
    scan = Session.query.get(session_id)
    if not scan:
        abort(404)
    fs = SessionForm().bind(scan, data=request.form or None)
    if request.method=='POST' and fs.validate():
        if not g.user.is_superuser():
            flash("Permission Denied")
            return redirect(request.url)
        fs.sync()
        try:
            db_session.commit()
            flash("Sucess: Session Modified")
        except:
            flash("Failed to update database")
            db_session.rollback()
        return redirect(request.url)
    if g.user.is_superuser():    
        return render_template('scan_form.html', scan=scan,
                               form=fs)
    return render_template('session.html', scan=scan)

@frontend.route('/session/<int:session_id>/problem/delete/')
@superuser_only
def del_problem(session_id):
    scan = Session.query.get(session_id)
    if not scan:
        abort(404)
    prob = scan.problem
    if not scan.problem:
        abort(404)
    try:
        db_session.delete(prob)
        db_session.commit()
        flash("Success: Removed billing correction", category='success')
    except:
        db_session.rollback()
        flash("Database error", category='error')
    return redirect(url_for('edit_session', session_id=scan.id))   
        
@frontend.route('/session/<int:session_id>/problem/', methods=['GET', 'POST'])
@authorized_users_only
def problem(session_id):
    scan = Session.query.get(session_id)
    if not scan:
        abort(404)
    prob = scan.problem if scan.problem else Problem(scan)
    # Lame ass formalchemy cannot handle a pending object
    # without id. Check for this and remove it from the scan
    # if needed
    if prob in db_session and not prob.id:
        db_session.expunge(prob)
    fs = ProblemForm().bind(prob, data=request.form or None)
    if request.method=='POST' and fs.validate():
        if not g.user.is_superuser():
            abort(403)
        fs.sync()
        try:
            prob.scan = scan
            db_session.add(prob)
            db_session.commit()
            flash("Sucess: Problem added or modified", category='success')
        except:
            flash("Failed: Could not update database", category='error')
            db_session.rollback()
        return redirect(url_for('edit_session', session_id=scan.id))    
    if g.user.is_superuser():
        return render_template('problem_form.html', scan=scan,
                               form=fs)
    return render_template('problem_request.html', scan=scan, form=ProblemRequestForm())

@frontend.route('/session/<int:session_id>/problem/usersubmit', methods=['POST'])
@authorized_users_only
def problem_request(session_id):
    scan = Session.query.get(session_id)
    if not scan:
        abort(404)
    form = ProblemRequestForm()
    if form.validate_on_submit():
        flash("We've received your report, you'll be notified of any changes to your invoice", 
              category='success')
        return redirect(url_for("edit_session", session_id=session_id))
    return redirect(url_for('problem', session_id=session_id))
