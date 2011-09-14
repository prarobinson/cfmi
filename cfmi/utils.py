import os
import pickle
from datetime import timedelta, date, datetime
from os.path import exists
from subprocess import Popen

from flask import (render_template, abort, request, g, url_for,
                   current_app)

from cfmi.database.dicom import Series, DicomSubject 
from cfmi.database.newsite import (User, Project, Session, Invoice, Problem)

def make_archive(filename):
    path = get_archive_path(filename)
    lockpath = path+".part"
    if exists(lockpath):
        return False
    subject = filename.split(".")[0]
    r = find_series_or_404(subject)
    exten = ".".join(filename.split(".")[1:])
    valid_formats = ['tar', 'zip', 'tar.bz2']
    valid_formats += [".".join(["nii", format]) for format in valid_formats]
    # Default to raw+bz2 if we have an out of spec extension
    exten = exten if exten in valid_formats else None
    if not exten: abort(403)
    filename = "{0}.{1}".format(subject, exten)
    os.mknod(lockpath, 0660)
    Popen(["compress.sh", subject, exten,
          current_app.config['DICOM_ARCHIVE_FOLDER'], g.user.email])
    return True

def get_archive_path(filename):
    return current_app.config['DICOM_ARCHIVE_FOLDER']+filename

def find_series_or_404(subject):
    """ find_series_or_404

    Returns a query object with filtered for subject and optional
    'program' and 'date' passed as GET args in the current request

    find_series_or_404() will 404 if the subject is not found, but
    return an empty query object if the subjects exists and the series
    are filtered out
    
    """
    r = Series.query.join(DicomSubject).filter(
        DicomSubject.name==subject)
    if not r.all():
        abort(404)
    if 'program' in request.args:
        r = r.filter(
            Series.program_name.contains(request.args['program']))
    if 'date' in request.args:
        year, month, day = request.args['date'].split('-')
        bot = date(int(year), int(month), int(day))
        oneday = timedelta(days=1)
        top = bot + oneday
        r = r.filter(Series.date<top).filter(Series.date>bot)
    return r

