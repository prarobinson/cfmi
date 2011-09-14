from flask import Flask, g, session
from flaskext.sqlalchemy import SQLAlchemy
from flaskext.cache import Cache

from cfmi.settings import DefaultConfig

db = SQLAlchemy()
cache = Cache()

def create_app(config=None):
    app = Flask(__name__)
    
    # Load default Values
    app.config.from_object(DefaultConfig())

    # Override with values from object argument
    if config is not None:
        app.config.from_object(config)

    # Load production values from the module specified by the
    # CFMI_CONFIG envvar
    app.config.from_envvar('CFMI_CONFIG', silent=True)

    db.init_app(app)
    cache.init_app(app)

    from cfmi.auth import auth
    app.register_blueprint(auth, subdomain='auth')

    from cfmi.imaging import imaging, imaging_api
    app.register_blueprint(imaging, subdomain='imaging')
    app.register_blueprint(imaging_api, subdomain='imaging',
                           url_prefix='/api')

    from cfmi.billing import billing, billing_api
    app.register_blueprint(billing, subdomain='billing')
    app.register_blueprint(billing_api, subdomain='billing',
                           url_prefix='/api')

    from cfmi.homepage import homepage
    app.register_blueprint(homepage)
    
    #from cfmi.scheduling import scheduling, scheduling_api
    #app.register_blueprint(scheduling, subdomain="schedule")
    #app.register_blueprint(scheduling_api, subdomain="schedule",
    #                       url_prefix='/api')

    from cfmi.database.newsite import User
    @app.before_request
    def before_request():
        g.user = None
        if 'user_id' in session:
            g.user = User.query.get(session['user_id'])
    return app
