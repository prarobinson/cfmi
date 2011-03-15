from flask import Flask, g, session

from cfmi.common.database.newsite import User, init_engine, Base, db_session
from cfmi.common.database.dicom import (
    init_engine as init_dicom, Base as Base_dicom, 
    db_session as db_session_dicom)

from cfmi.common.views import auth
from cfmi.imaging.views import frontend

def create_app(testing=False):
    app = Flask(__name__)
    app.config.setdefault('NEWSITE_DB_STRING', 'sqlite:///')
    app.config.setdefault('DICOM_DB_STRING', 'sqlite:///')
    if not testing:
        app.config.from_object('cfmi.imaging.settings')
    init_engine(app.config['NEWSITE_DB_STRING'])
    init_dicom(app.config['DICOM_DB_STRING'])
    Base.query = db_session.query_property()
    Base_dicom.query = db_session_dicom.query_property()
    #app.register_module(api, url_prefix='/api')
    app.register_module(frontend)
    app.register_module(auth)
    # Establish hooks common to all modules
    @app.after_request
    def after_request(response):
            db_session.remove()
            db_session_dicom.remove()
            return response

    @app.before_request
    def before_request():
        g.user = None
        if 'user_id' in session:
            g.user = User.query.get(session['user_id'])

    return app
