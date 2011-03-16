import pickle
import zmq
from datetime import timedelta, date
from subprocess import call

from flask import (Module, render_template, abort)

from cfmi.common.database.dicom import Series 

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
