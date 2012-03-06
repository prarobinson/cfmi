from flask import (Blueprint, jsonify, abort, request) 

from cfmi.auth import (
    login_required, authorized_users_only, superuser_only)
from cfmi.database.dicom import (Series)
from cfmi.database.newsite import Project, User, Subject 

api = Blueprint('imaging_api', __name__, static_folder='static',
                template_folder='templates')

@api.route('/path/<subject>')
def get_path(subject):
    """ get path

    Return the paths of all series by subject filtered by
    find_series(). See find_series() for all get args related to
    filtering
   
    """
    subj = Subject.query.filter(Subject.name==subject).first()
    if not subj:
        abort(404)
    return "\n".join([series.get_path() for series in subj.get_series()])

@api.route('/id/<subject>')
def get_id(subject):
    """ get_id

    Return the id of all series by subject filtered by
    find_series(). See find_series() for all get args related to
    filtering

    """
    subj = Subject.query.filter(Subject.name==subject).first()
    if not subj:
        abort(404)
    return "\n".join([series.id for series in subj.get_series()])

@api.route('/info/<series_id>')
def get_info(series_id):
    r = Series.query.get_or_404(series_id)
    return jsonify(id=r.id, date=r.date.strftime("%Y/%m/%d"),
                   subject=r.subject.name, program=r.program_name)

@api.route('/project/<project_id>')
@login_required
def project(project_id):
    proj = Project.query.get_or_404(project_id)
    return jsonify(name=proj.name, id=proj.id, shortname=proj.shortname(), 
                   subjects=[subject.name for subject in proj.subjects])

@api.route('/subject/<subject>')
@authorized_users_only
def subject(subject):
    subj = Subject.query.filter(Subject.name==subject).first()
    return jsonify(name=subject, series=[[series.id, series.date.strftime(
                    "%Y/%m/%d")] for series in subj.get_series()])

@api.route('/series/<series_id>')
@authorized_users_only
def series(series_id):
    ser = Series.query.get(series_id)
    if not ser:
        abort(404)
    date = ser.date.strftime("%m/%d/%Y %H:%M")
    return jsonify(program=ser.program_name, id=ser.id, 
                   date=date, subject=ser.subject.name)


