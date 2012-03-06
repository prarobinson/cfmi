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
from cfmi.database.newsite import (User, Project, Session, Invoice, Problem, Subject)

def flatten(obj, attrib_filter=None):
    goodstuff = copy(obj.__dict__)
    if attrib_filter:
        for key in obj.__dict__:
            if not key in attrib_filter:
                del goodstuff[key]
    for key, value in obj.__dict__.iteritems():
        if isinstance(value, (User, Project, Session, Invoice, Problem)):
            del goodstuff[key]
        if isinstance(value, [].__class__):
            goodstuff[key] = [flatten(subitem, attrib_filter=['id','username']) for subitem in value]
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
    if 'nii' in filename.split("."):
        exten_depth += 1
    if 'bz2' in filename.split("."):
        exten_depth += 1
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
    exten = exten if exten in valid_formats else abort(403)
    os.mknod(lockpath, 0660)
    script_path = '/'.join([current_app.config['BASE_PATH'], 
	"cfmi/cfmi/imaging/scripts/compress.sh"])
    Popen([script_path, subject, exten,
          current_app.config['DICOM_ARCHIVE_FOLDER'], g.user.email])
    return True

def get_archive_path(filename):
    return current_app.config['DICOM_ARCHIVE_FOLDER']+filename
