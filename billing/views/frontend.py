from datetime import timedelta, date
from subprocess import call

from flask import (
    render_template, request, session, g, redirect, url_for, abort, 
    flash, send_file, escape, current_app, Module)

from cfmi.billing.models import (User, Project, Session, Problem, Invoice, 
                                 db_session)
from cfmi.common.auth.decorators import (superuser_only, login_required,
                                         authorized_users_only)

from cfmi.billing.utils import (
    total_ytd, total_last_month, limit_month, gchart_ytd_url)

from formalchemy import FieldSet
from cfmi.billing.forms import ROSessionForm, SessionForm, ProblemForm

frontend = Module(__name__)

## Views

@frontend.route('/')
@login_required
def index():
    return render_template('index.html')

@frontend.route('/reconcile/')
@superuser_only
def reconcile():
    outstanding = Invoice.query.filter(Invoice.reconciled==False)
    return render_template('reconcile.html', invoice_list=outstanding)

@frontend.route('/stats/')
@superuser_only
def statistics():
    return render_template('stats.html', ytd=total_ytd(), lastmonth=total_last_month(),
                           gchart_ytd_url=gchart_ytd_url())

@frontend.route('/batch/')
@superuser_only
def batch():
    return render_template('batch.html')

@frontend.route('/invoice/<invoice_id>')
@authorized_users_only
def invoice(id):
    inv = Invoice.query.get(invoice_id)
    if not inv:
        abort(404)
    return inv.render()

@frontend.route('/<pi_uname>/<int:year>/<int:month>/')
@login_required
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
        
    return render_template('scan_form.html', scan=scan,
                           form=fs)

@frontend.route('/session/<int:id>/problem/delete/')
@superuser_only
def del_problem(id):
    scan = Session.query.get(id)
    if not scan:
        abort(404)
    prob = scan.problem
    if not scan.problem:
        abort(404)
    try:
        db_session.delete(prob)
        db_session.commit()
        flash("Removed billing correction")
    except:
        db_session.rollback()
        flash("Database error")
    return redirect(url_for('edit_session', session_id=id))   
        
@frontend.route('/session/<int:id>/problem/', methods=['GET', 'POST'])
@superuser_only
def problem(id):
    scan = Session.query.get(id)
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
        fs.sync()
        try:
            prob.scan = scan
            db_session.add(prob)
            db_session.commit()
            flash("Sucess: Problem added or modified")
            return redirect(url_for('edit_session', session_id=id))
        except:
            flash("Failed: Could not update database")
            db_session.rollback()

    return render_template('problem_form.html', scan=scan,
                           form=fs)

