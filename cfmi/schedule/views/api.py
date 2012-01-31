from flask import (Blueprint, render_template,
                   url_for, abort, current_app,
                   request, jsonify)

from cfmi.database.newsite import Session
#from cfmi.schedule.models import Day, Week
from cfmi.auth import (superuser_only, login_required,
                       authorized_users_only)
from cfmi.utils import flatten

api = Blueprint('schedule_api', __name__, static_folder="../static",
                     template_folder='../templates')

# Views
@api.route('/')
def index():
    return render_template("homepage.html")

@api.route('/session/<int:session_id>')
@authorized_users_only
def session_handler(session_id):
    session = Session.query.get(session_id)
    if not session: 
        return abort(404)
    return(jsonify(flatten(session)))
