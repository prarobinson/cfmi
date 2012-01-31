import os
import pickle
from datetime import timedelta, date, datetime
from os.path import exists
from subprocess import Popen
from copy import copy
from decimal import Decimal

from flask import (render_template, abort, request, g, url_for,
                   current_app)

from cfmi.database.dicom import Series, DicomSubject 
from cfmi.database.newsite import (User, Project, Session, Invoice, Problem)

def flatten(obj, attrib_filter=None):
    goodstuff = copy(obj.__dict__)
    if attrib_filter:
        for key in obj.__dict__:
            if not key in attrib_filter:
                del goodstuff[key]
    for key, value in obj.__dict__.iteritems():
        if isinstance(value, (User, Project, Session, Invoice, Problem, [].__class__)):
            del goodstuff[key]
    for key, value in goodstuff.iteritems():
        if isinstance(value, datetime):
            goodstuff[key]=value.strftime("%m/%d/%Y %H:%M")
        if isinstance(value, date):
            goodstuff[key]=value.strftime("%m/%d/%Y")
        if isinstance(value, Decimal):
            goodstuff[key]=float(value)
    if '_sa_instance_state' in goodstuff:
        del goodstuff['_sa_instance_state']
    return goodstuff

def parse_filename(filename):
    exten_depth = 1
    if filename.split(".")[-2] == "nii":
        exten_depth = 2
    subject = '.'.join(filename.split(".")[:-exten_depth])
    exten = ".".join(filename.split(".")[-exten_depth:])
    return subject, exten

def make_archive(filename):
    path = get_archive_path(filename)
    lockpath = path+".part"
    if exists(lockpath):
        return False
    subject, exten = parse_filename(filename)
    r = find_series_or_404(subject)
    valid_formats = ['tar', 'zip', 'tar.bz2']
    valid_formats += [".".join(["nii", format]) for format in valid_formats]
    # Default to raw+bz2 if we have an out of spec extension
    exten = exten if exten in valid_formats else abort(403)
    os.mknod(lockpath, 0660)
    script_path = '/'.join([current_app.config['BASE_PATH'], 
	"cfmi/cfmi/imaging/scripts/compress.sh"])
    Popen([script_path, subject, exten,
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

