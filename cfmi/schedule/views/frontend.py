from flask import (Blueprint, render_template,
                   url_for, abort, current_app,
                   request)

from cfmi.auth import (login_required)

frontend = Blueprint('schedule', __name__, static_folder="../static",
                     template_folder='../templates')

# Views
@frontend.route('/')
def index():
    return render_template("homepage.html")
