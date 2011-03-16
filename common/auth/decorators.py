import functools

from flask import (g, url_for, abort, redirect, request)

from cfmi.common.database.newsite import Subject, Project, Session, Invoice

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
        if 'session_id' in kwargs:
            project = Session.query.get(
                kwargs['session_id']).project
        if 'invoice_id' in kwargs:
            project = Invoice.query.get(
                kwargs['invoice_id']).project
        #if self.app.config['CFMIAUTH_USING_DICOM']:
        #    if 'series_id' in kwargs:
        #        subj_str = Dicom.Series.query.get(
        #            kwargs['series_id']).subject.name
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
