from flask import Flask, g, session
from flaskext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
db = SQLAlchemy(app)
from cfmi.auth import auth
app.config.from_object('cfmi.settings')
app.register_blueprint(auth)

@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
            g.user = User.query.get(session['user_id'])
