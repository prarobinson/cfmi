from flask import (Module, jsonify, abort) 

from cfmi.common.auth.decorators import (
        login_required, authorized_users_only)
from cfmi.common.database.dicom import (Series, Subject as DicomSubject)
from cfmi.common.database.newsite import Project

from cfmi.imaging.utils import find_series_or_404


api = Module(__name__)

@api.route('/path/<subject>')
def get_path(subject):
    """ get path

    Return the paths of all series by subject filtered by
    find_series(). See find_series() for all get args related to
    filtering
   
    """
    r = find_series_or_404(subject)
    return "\n".join([series.get_path() for series in r])

@api.route('/id/<subject>')
def get_id(subject):
    """ get_id

    Return the id of all series by subject filtered by
    find_series(). See find_series() for all get args related to
    filtering

    """
    r = find_series_or_404(subject)
    return "\n".join([series.id for series in r])

@api.route('/info/<series_id>')
def get_info(series_id):
    r = Series.query.get_or_404(series_id)
    return jsonify(id=r.id, date=r.date.strftime("%Y/%m/%d"),
                   subject=r.subject.name, program=r.program_name)

@api.route('/project/<project_id>')
@login_required
def project(project_id):
    proj = Project.query.get(project_id)
    if not proj:
        abort(404)
    return jsonify(name=proj.name, id=proj.id, shortname=proj.shortname(), 
                   subjects=proj.get_subjects())

@api.route('/subject/<subject>')
@authorized_users_only
def subject(subject):
    subj = DicomSubject.query.filter(DicomSubject.name==subject).first()
    if not subj:
        abort(404)
    return jsonify(name=subj.name, series=subj.get_all_series())

@api.route('/series/<series_id>')
@authorized_users_only
def series(series_id):
    ser = Series.query.get(series_id)
    if not ser:
        abort(404)
    date = ser.date.strftime("%m/%d/%Y %H:%M")
    return jsonify(program=ser.program_name, id=ser.id, 
                   date=date, subject=ser.subject.name)
