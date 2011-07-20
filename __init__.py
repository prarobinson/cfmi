from flask import Flask, g, session
from flaskext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
db = SQLAlchemy(app)

app.config.from_object('cfmi.settings')

from cfmi.auth import auth
app.register_blueprint(auth)

from cfmi.imaging import imaging, imaging_api
app.register_blueprint(imaging, subdomain='imaging')
app.register_blueprint(imaging_api, subdomain='imaging',
                       url_prefix='/api')

from cfmi.database.newsite import User
@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
            g.user = User.query.get(session['user_id'])
