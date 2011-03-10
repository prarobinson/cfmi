from calendar import monthrange
from datetime import timedelta, date
from subprocess import call
from time import sleep
from operator import and_
import functools

from flask import render_template, request, session, g, redirect, \
    url_for, abort, flash, send_file, escape

from common.database.newsite import Project, User, Problem, Invoice, Session

from formalchemy import FieldSet
from billing.forms import ROSessionForm, SessionForm, ProblemForm

from billing import app

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

## Utility functions

def login_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not g.user:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return wrapper

def total_ytd():
    year_start = date(date.today().year, 7, 1)
    target_scans = Session.query.filter(
            Session.sched_start>=year_start).filter(
            Session.approved==True).filter(
            Session.cancelled==False).filter(
            Session.sched_start<=date.today())
    total = sum(float(x.cost()) for x in target_scans)
    return "${0:.2f}".format(total)

def total_last_month():
    today = date.today()
    year = today.year
    month = today.month-1
    total = sum(float(x.cost()) for x in sessions_from_month(year, month))
    return "${0:.2f}".format(total)
            
def active_pis():
    return User.query.filter(User.pi_projects!=None).all()

def sessions_from_month(year, month):
    isoday, numdays = monthrange(year, month)
    min_date = date(year, month, 1)
    max_date = date(year, month, numdays)
    return Session.query.filter(
        Session.sched_start>=min_date).filter(
        Session.sched_start<=max_date).filter(
            Session.approved==True).filter(
            Session.cancelled==False)

def limit_month(queryset, year, month):
    isoday, numdays = monthrange(year, month)
    min_date = date(year, month, 1)
    max_date = date(year, month, numdays)
    return queryset.filter(Session.sched_start>=min_date).filter(
        Session.sched_start<=max_date).filter(
        Session.approved==True).filter(
            Session.cancelled==False)

def active_projects():
    return Project.query.filter(Project.is_active==True)

def generate_invoices(year, month):
    for project in active_projects():
        ses = sessions_from_month(year, month).filter(
            Session.project==project).all()
        start_date = date(year, month, 1)
        if len(ses):
            # If there is something to bill on this project,
            # Then generate the cannonical invoice
            if False in (x.is_devel() for x in ses):
                # There are non-development scans
                if not len(Invoice.query.filter(
                        Invoice.project==project).filter(
                        Invoice.date==start_date).all()):
                    # If the invoice exists already, don't bother
                    inv = Invoice(project, date)
                    db.session.add(inv)
                    try:
                        db.session.commit()
                    except:
                        db.session.rollback()

def due_invoices():
    today = date.today()
    net30 = timedelta(days=30)
    return Invoice.query.filter(
        Invoice.reconciled==False).filter(Invoice.date<today-net30)


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
    inv = Invoice.query.get_or_404(id)
    return inv.render_html()

@app.route('/logout/')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out")
    return redirect(url_for('index'))

@app.route('/login', methods = ['GET','POST'])
def login():
    # User is already logged in
    if g.user:
        if 'next' in request.args:
            return redirect(request.args['next'])
        else:
            return redirect(url_for('index'))

    # Try to authenticate
    if request.method=='POST':
        uname = request.form['username']
        passwd = request.form['password']
        try:
            user = User.query.filter(User.username==uname).one()
        except:
            # Invalid user
            flash('Invalid user/pass')
            return redirect(request['url'])
        if user.auth(passwd):
            # User entered the correct password
            session['user_id'] = user.id
            if 'next' in request.args:
                return redirect(request.args['next'])
            return redirect(url_for('index'))
        
        # Wrong password
        flash('Invalid user/pass')
        return redirect(url_for('login'))
    
    else:
        # For method 'GET'
        return render_template('login.html')


@app.route('/<pi_uname>/<int:year>/<int:month>/')
@login_required
def pi_month_view(pi_uname, year, month):
    pi = User.query.filter(User.username==pi_uname).first_or_404()
    
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
@login_required
def edit_session(id):
    scan = Session.query.get_or_404(id)
    fs = SessionForm().bind(scan, data=request.form or None)
    if request.method=='POST' and fs.validate():
        if not g.user.is_superuser():
            flash("Permission Denied")
            return redirect(request.url)
        fs.sync()
        try:
            db.session.commit()
            flash("Sucess: Session Modified")
        except:
            flash("Failed to update database")
            db.session.rollback()
        return redirect(request.url)
        
    return render_template('scan_form.html', scan=scan,
                           form=fs)

@app.route('/scan/<int:id>/problem/delete/')
@login_required
def del_problem(id):
    if not g.user.is_superuser():
        abort(403)
    scan = Session.query.get_or_404(id)
    prob = scan.problem
    if not scan.problem:
        abort(404)
    try:
        db.session.delete(prob)
        db.session.commit()
        flash("Removed billing correction")
    except:
        db.session.rollback()
        flash("Database error")
    return redirect(url_for('edit_session', id=id))   
        
@app.route('/scan/<int:id>/problem/', methods=['GET', 'POST'])
@login_required
def problem(id):
    if not g.user.is_superuser():
        abort(403)

    scan = Session.query.get_or_404(id)
    prob = scan.problem if scan.problem else Problem(scan)
    # Lame ass formalchemy cannot handle a pending object
    # without id. Check for this and remove it from the scan
    # if needed
    if prob in db.session and not prob.id:
        db.session.expunge(prob)
    fs = ProblemForm().bind(prob, data=request.form or None)
    if request.method=='POST' and fs.validate():
        fs.sync()
        try:
            prob.scan = scan
            db.session.add(prob)
            db.session.commit()
            flash("Sucess: Problem added or modified")
            return redirect(url_for('edit_session', id=id))
        except:
            flash("Failed: Could not update database")
            db.session.rollback()

    return render_template('problem_form.html', scan=scan,
                           form=fs)

# API View
