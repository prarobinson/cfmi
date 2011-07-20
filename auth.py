import functools
from flask import (Blueprint, url_for, redirect, session, flash, g,
                   request, render_template, current_app, abort)

from cfmi.database.newsite import (User, Subject, Project, Session, Invoice)

auth = Blueprint('auth', __name__)

@auth.route('/login/', methods = ['GET','POST'])
def login():
    if not g.user:
        if request.method=='POST':
            uname = request.form['username']
            passwd = request.form['password']
            if not uname:
                flash('Invalid user/pass', category='error')
                return render_template('login.html')
            user = User.query.filter(
                User.username==uname).first()
            if user: 
                if user.auth(passwd) or current_app.config['TESTING']:
                    session['user_id'] = user.id
            else:
                flash('Invalid user/pass', category='error')
        else:
            # For method 'GET'
            return render_template('login.html')
    if 'next' in request.args:
        return redirect(request.args['next'])
    else:
        return redirect('/')

@auth.route('/logout/')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out", category='info')
    return redirect('/')

def authorized_users_only(f):
    """ 
    Ensures the logged in user is authorized for the subject 
    in the kwarg 'subject' 
    """
    @functools.wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        subj_str = None
        project = None
        if g.user.is_superuser():
            return f(*args, **kwargs)
        if 'filename' in kwargs:
            subj_str = kwargs['filename'].split(".")[0]
        if 'subject' in kwargs:
            subj_str = kwargs['subject']
        if 'session_id' in kwargs:
            session = Session.query.get(
                kwargs['session_id'])
            if not session: abort(404)
            project = session.project
        if 'invoice_id' in kwargs:
            invoice = Invoice.query.get(
                kwargs['invoice_id'])
            if not invoice: abort(404)
            project = invoice.project
        if 'pi_uname' in kwargs:
            if g.user.username == kwargs['pi_uname']:
                return f(*args, **kwargs)
        #if self.app.config['CFMIAUTH_USING_DICOM']:
        #    if 'series_id' in kwargs:
        #        subj_str = Dicom.Series.query.get(
        #            kwargs['series_id']).subject.name
        if subj_str:
            project = Subject.query.filter(
                Subject.name==subj_str).first().project
        if 'project_id' in kwargs:
            project = Project.get(kwargs['project_id'])
        if project:
            if project.auth(g.user):
                return f(*args, **kwargs)
        return abort(403)
    return wrapper

def login_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not g.user:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return wrapper

def superuser_only(f):
    @functools.wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if not g.user.is_superuser():
            abort(403)
        return f(*args, **kwargs)
    return wrapper
