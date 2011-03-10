import pam
import functools

from flask import g, abort, url_for, redirect, request

from sqlalchemy.orm import mapper

from common.database.newsite import Project, Subject
from common.database.newsite import cleanup_session as cleanup_newsite
from common.database.dicom import DicomSeries
from common.database.dicom import cleanup_session as cleanup_dicom

def cleanup_session():
    cleanup_newsite()
    cleanup_dicom()

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
