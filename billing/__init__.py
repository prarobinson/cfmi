from flask import Flask, g, session

from cfmi.common.database.newsite import init_engine, db_session
from cfmi.common.auth.views import auth
from cfmi.billing.views import api
from cfmi.billing.views import frontend

def create_app(testing=False):
    app = Flask(__name__)
    app.config.setdefault('NEWSITE_DB_STRING', 'sqlite:///')
    if not testing:
        app.config.from_object('cfmi.billing.settings')
    init_engine(app.config['NEWSITE_DB_STRING'])
    app.register_module(api, url_prefix='/api')
    app.register_module(frontend)
    app.register_module(auth)
    from cfmi.billing.models import User
    # Establish hooks common to all modules
    @app.after_request
    def after_request(response):
            db_session.remove()
            return response

    @app.before_request
    def before_request():
        g.user = None
        if 'user_id' in session:
            g.user = User.query.get(session['user_id'])

    return app
