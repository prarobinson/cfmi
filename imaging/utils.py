import os
import pickle
import zmq
from datetime import timedelta, date
from subprocess import call

from flask import (Module, render_template, abort, request, g, url_for,
                   current_app)

from cfmi.common.database.dicom import Series, Subject 

def make_archive(filename):
    path = current_app.config['DICOM_ARCHIVE_FOLDER']+filename
    subject = filename.split(".")[0]
    r = find_series_or_404(subject)
    exten = ".".join(filename.split(".")[1:])
    valid_formats = ['tar', 'zip', 'tar.bz2']
    valid_formats += [".".join(["nii", format]) for format in valid_formats]
    # Default to raw+bz2 if we have an out of spec extension
    exten = exten if exten in valid_formats else None
    if not exten: abort(403)
    filename = "{0}.{1}".format(subject, exten)
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5555")
    os.mknod(path+'.part', 0660)
    socket.send(pickle.dumps((g.user.email, subject, exten)))

def find_series_or_404(subject):
    """ find_series_or_404

    Returns a query object with filtered for subject and optional
    'program' and 'date' passed as GET args in the current request

    find_series_or_404() will 404 if the subject is not found, but
    return an empty query object if the subjects exists and the series
    are filtered out
    
    """
    r = Series.query.join(Subject).filter(
        Subject.name==subject)
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

def file_ready(filename):
    path = current_app.config['DICOM_ARCHIVE_FOLDER']+filename
    tmpfile = path+'.part'
    if os.path.exists(path):
        return True
    if not os.path.exists(tmpfile):
        make_archive(filename)
    return False
