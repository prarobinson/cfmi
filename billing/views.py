from datetime import timedelta, date
from subprocess import call

from flask import (
    render_template, request, session, g, redirect, url_for, abort, 
    flash, send_file, escape)

from cfmi.billing import app, cfmiauth
from cfmi.billing.models import User, Project, Session, Problem, Invoice


from cfmi.billing.utils import (
    total_ytd, total_last_month, active_pis, due_invoices, limit_month)

from formalchemy import FieldSet
from cfmi.billing.forms import ROSessionForm, SessionForm, ProblemForm


## Filters
@app.template_filter()
def datef(value, format='%m/%d/%Y %H:%M'):
    return value.strftime(format)

## Flask Hooks
@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])

## Views

@app.route('/')
def index():
    return render_template('index.html', 
                           last_month=total_last_month(), 
                           YTD=total_ytd(),
                           active_pis=active_pis(),
                           due=due_invoices())

@app.route('/invoice/<id>')
def invoice(id):
    inv = Invoice.query.get(id)
    if not inv:
        abort(404)
    return inv.render()

@app.route('/<pi_uname>/<int:year>/<int:month>/')
@cfmiauth.login_required
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

@app.route('/session/<int:id>/', methods=['GET', 'POST'])
@cfmiauth.login_required
def edit_session(id):
    scan = Session.query.get(id)
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

@app.route('/scan/<int:id>/problem/delete/')
@cfmiauth.login_required
def del_problem(id):
    if not g.user.is_superuser():
        abort(403)
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
    return redirect(url_for('edit_session', id=id))   
        
@app.route('/scan/<int:id>/problem/', methods=['GET', 'POST'])
@cfmiauth.login_required
def problem(id):
    if not g.user.is_superuser():
        abort(403)

    scan = Session.query.get(id)
    if not scan:
        abort(404)
    prob = scan.problem if scan.problem else Problem(scan)
    # Lame ass formalchemy cannot handle a pending object
    # without id. Check for this and remove it from the scan
    # if needed
    if prob in newsite.db_session and not prob.id:
        db_session.expunge(prob)
    fs = ProblemForm().bind(prob, data=request.form or None)
    if request.method=='POST' and fs.validate():
        fs.sync()
        try:
            prob.scan = scan
            db_session.add(prob)
            db_session.commit()
            flash("Sucess: Problem added or modified")
            return redirect(url_for('edit_session', id=id))
        except:
            flash("Failed: Could not update database")
            db_session.rollback()

    return render_template('problem_form.html', scan=scan,
                           form=fs)

