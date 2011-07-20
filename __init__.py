from flask import Flask, g, session
from flaskext.sqlalchemy import SQLAlchemy
from flaskext.cache import Cache

app = Flask(__name__)
app.config.from_object('cfmi.settings')

db = SQLAlchemy(app)
cache = Cache(app)

from cfmi.auth import auth
app.register_blueprint(auth)

from cfmi.imaging import imaging, imaging_api
app.register_blueprint(imaging, subdomain='imaging')
app.register_blueprint(imaging_api, subdomain='imaging',
                       url_prefix='/api')

from cfmi.billing import billing, billing_api
app.register_blueprint(billing, subdomain='billing')
app.register_blueprint(billing_api, subdomain='billing',
                       url_prefix='/api')

from cfmi.database.newsite import User
@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
            g.user = User.query.get(session['user_id'])
