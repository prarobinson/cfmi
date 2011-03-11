from datetime import date, timedelta
from subprocess import call
import os
import pickle
import zmq
import functools

from flask import (request, redirect, abort, send_file, jsonify, g,
                   session, render_template, url_for, abort, flash,
                   make_response)

from cfmi.imaging import app, dicom, newsite, cfmiauth

# Globals

## Flask Hooks
@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = newsite.User.query.get(session['user_id'])

## Utility Functions

def make_archive(filename):
    subject = filename.split(".")[0]
    exten = ".".join(filename.split(".")[1:])
    valid_formats = ['tar', 'tar.gz', 'zip','tar.xz', 
                     'tar.bz2']
    valid_formats += [".".join(["nii", format]) for format in valid_formats]
    # Default to raw+bz2 if we have an out of spec extension
    exten = exten if exten in valid_formats else "tar.bz2"
    filename = "{0}.{1}".format(subject, exten)
    r = find_series_or_404(subject)
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5555")
    socket.send(
        pickle.dumps((g.user.email, subject, [x.get_path() for x in r], 
                      exten)))
    status = socket.recv()
    return render_template("processing.html", url=url_for(
            'download', filename=filename))

def find_series_or_404(subject):
    """ find_series_or_404

    Returns a query object with filtered for subject and optional
    'program' and 'date' passed as GET args in the current request

    find_series_or_404() will 404 if the subject is not found, but
    return an empty query object if the subjects exists and the series
    are filtered out
    
    """
    r = dicom.Series.query.join(dicom.Subject).filter(
        dicom.Subject.name==subject)
    if not r.all():
        abort(404)
    if 'program' in request.args:
        r = r.filter(
            dicom.Series.program_name.contains(request.args['program']))
    if 'date' in request.args:
        year, month, day = request.args['date'].split('-')
        bot = date(int(year), int(month), int(day))
        oneday = timedelta(days=1)
        top = bot + oneday
        r = r.filter(dicom.Series.date<top).filter(dicom.Series.date>bot)
    return r

# API Views
@app.route('/')
@cfmiauth.login_required
def index():
    return render_template("layout.html") 

@app.route('/api/path/<subject>')
def get_path(subject):
    """ get path

    Return the paths of all series by subject filtered by
    find_series(). See find_series() for all get args related to
    filtering
   
    """
    r = find_series_or_404(subject)
    return "\n".join([series.get_path() for series in r])

@app.route('/api/id/<subject>')
def get_id(subject):
    """ get_id

    Return the id of all series by subject filtered by
    find_series(). See find_series() for all get args related to
    filtering

    """
    r = find_series_or_404(subject)
    return "\n".join([series.id for series in r])

@app.route('/api/info/<series_id>')
def get_info(series_id):
    r = dicom.Series.query.get_or_404(series_id)
    return jsonify(id=r.id, date=r.date.strftime("%Y/%m/%d"),
                   subject=r.subject.name, program=r.program_name)

@app.route('/download/<filename>', methods=['GET','HEAD'])
@cfmiauth.authorized_users_only
def download(filename):
    """ get_dicom

    Queue the creation of an archive containing all subject dicom
    files and redirect to the eventual location.

    The heavy lifting is does by the dataserver component that lives
    in dataserver.py

    """
    if not os.path.exists(app.config['DICOM_ARCHIVE_FOLDER']+filename):
        # The file doesn't exist, lets start making it
        return make_archive(filename)
    if os.stat(app.config['DICOM_ARCHIVE_FOLDER']+filename)[6] == 0:
        # The file exits but is 0 bytes, the dataserver is working 
        # on it already, send them to the waiting page
        return render_template("processing.html", url=url_for(
                'download', filename=filename))

    # If we've made it this far, we're ready to send the file
    if not app.config["DEBUG"]:
        # Use nginx for the heavy lifting on the prod setup
        r = make_response()
        r.headers['Content-Disposition'] = "attachment"
        r.headers['X-Accel-Redirect'] = "/dicom/" + filename
        return r
    else:
        return send_file(
            app.config['DICOM_ARCHIVE_FOLDER']+filename, 
            as_attachment=True)

@app.route('/download/<filename>/ready')
@cfmiauth.authorized_users_only
def file_ready(filename):
    if not os.path.exists(app.config['DICOM_ARCHIVE_FOLDER']+filename):
        abort(404)
    if not os.stat(app.config['DICOM_ARCHIVE_FOLDER']+filename)[6]:
        abort(404)
    return render_template("processing.html", url=url_for(
                'download', filename=filename))
    
@app.route('/api/project/<project_id>')
@cfmiauth.login_required
def project(project_id):
    proj = newsite.Project.query.get(project_id)
    if not proj:
        abort(404)
    return jsonify(name=proj.name, id=proj.id, shortname=proj.shortname(), 
                   subjects=proj.get_subjects())

@app.route('/api/subject/<subject>')
@cfmiauth.authorized_users_only
def subject(subject):
    subj = dicom.Subject.query.filter(dicom.Subject.name==subject).first()
    if not subj:
        abort(404)
    return jsonify(name=subj.name, series=subj.get_all_series())

@app.route('/api/series/<series_id>')
@cfmiauth.authorized_users_only
def series(series_id):
    ser = dicom.Series.query.get(series_id)
    if not ser:
        abort(404)
    date = ser.date.strftime("%m/%d/%Y %H:%M")
    return jsonify(program=ser.program_name, id=ser.id, 
                   date=date, subject=ser.subject.name)
