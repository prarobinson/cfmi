import pam
import functools

from flask import (
    g, abort, url_for, redirect, request, render_template)

from sqlalchemy.orm import mapper

from common.database.newsite import Project, Subject, User
from common.database.newsite import cleanup_session as cleanup_newsite
from common.database.dicom import DicomSeries
from common.database.dicom import cleanup_session as cleanup_dicom

def cleanup_session():
    cleanup_newsite()
    cleanup_dicom()

# Decorators

def authorized_users_only(f):
    """ 
    Ensures the logged in user is authorized for the subject 
    in the kwarg 'subject' 
    """
    @functools.wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if g.user.is_superuser():
            return f(*args, **kwargs)
        if 'filename' in kwargs:
            subj_str = kwargs['filename'].split(".")[0]
        if 'subject' in kwargs:
            subj_str = kwargs['subject']
        if 'series_id' in kwargs:
            subj_str = DicomSeries.query.get(kwargs['series_id']).subject.name
        if subj_str:
            project = Subject.query.filter(
                Subject.name==subj_str).first().project
        if 'project_id' in kwargs:
            project = Project.get(kwargs['project_id'])
            
        if project.auth(g.user):
                return f(*args, **kwargs)
        return abort(403)

    return wrapper

def login_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not g.user:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return wrapper

# Standard Views

def register(app):
    @app.route('/login', methods = ['GET','POST'])
    def login():
        if not g.user:
            if request.method=='POST':
                uname = request.form['username']
                passwd = request.form['password']
                user = User.query.filter(User.username==uname).first()
                if user and user.auth(passwd):
                    session['user_id'] = user.id
                else:
                    flash('Invalid user/pass')
            else:
                # For method 'GET'
                return render_template('login.html')
        if 'next' in request.args:
            return redirect(request.args['next'])
        else:
            return redirect(url_for('index'))

    @app.route('/logout/')
    def logout():
        session.pop('user_id', None)
        flash("You have been logged out")
        return redirect(url_for('index'))

    @app.after_request
    def shutdown_session(response):
        cleanup_session()
        return response
