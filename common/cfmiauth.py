import pam
import functools

from flask import (
    g, abort, url_for, redirect, request, render_template, session)

from sqlalchemy.orm import mapper

from cfmi.common.database import Dicom, Newsite

# Decorators



# Standard Views

class Cfmiauth:
    def __init__(self, app, newsite, dicom=None):
        app = app
        app.config['CFMIAUTH_USING_DICOM'] = True if dicom else False
    
        @app.route('/login', methods = ['GET','POST'])
        def login():
            if not g.user:
                if request.method=='POST':
                    uname = request.form['username']
                    passwd = request.form['password']
                    user = newsite.User.query.filter(
                        newsite.User.username==uname).first()
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

        
    def authorized_users_only(self, f):
        """ 
        Ensures the logged in user is authorized for the subject 
        in the kwarg 'subject' 
        """
        @functools.wraps(f)
        @self.login_required
        def wrapper(*args, **kwargs):
            if g.user.is_superuser():
                return f(*args, **kwargs)
            if 'filename' in kwargs:
                subj_str = kwargs['filename'].split(".")[0]
            if 'subject' in kwargs:
                subj_str = kwargs['subject']
            if self.app.config['CFMIAUTH_USING_DICOM']:
                if 'series_id' in kwargs:
                    subj_str = Dicom.Series.query.get(
                        kwargs['series_id']).subject.name
            if subj_str:
                project = Subject.query.filter(
                    Subject.name==subj_str).first().project
            if 'project_id' in kwargs:
                project = Project.get(kwargs['project_id'])
            
            if project.auth(g.user):
                return f(*args, **kwargs)
            return abort(403)
        return wrapper

    def login_required(self, f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if not g.user:
                return redirect(url_for('login', next=request.url))
            return f(*args, **kwargs)
        return wrapper
