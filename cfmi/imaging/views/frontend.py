from os.path import exists
from flask import (Blueprint, send_file as flask_send_file, render_template,
                   url_for, abort, make_response, Module, current_app,
                   request)

from cfmi.auth import (login_required, authorized_users_only)
from cfmi.utils import (make_archive, find_series_or_404, get_archive_path)

frontend = Blueprint('imaging', __name__, static_folder="../static",
                     template_folder='../templates')

# Views
@frontend.route('/')
@login_required
def index():
    return render_template("imaging.html") 

@frontend.route('/download/<filename>', methods=['GET','HEAD'])
@authorized_users_only
def download(filename):
    path = get_archive_path(filename)
    if exists(path):
        return sendfile(filename)
    else:
        ## Hijack HEAD requests to check status, if the file is ready
        if request.method == 'HEAD':
            abort(404)
        make_archive(filename)
        return render_template("processing.html", url=url_for(
                'download', filename=filename))

def sendfile(filename):
    if current_app.config["DEBUG"]:
        # Use flask during development
        return flask_send_file(get_archive_path(filename),
                               as_attachment=True)
    else:
        # Use nginx for the heavy lifting on the prod setup
        r = make_response()
        r.headers['Content-Type']=""
        r.headers['Content-Disposition'] = "attachment"
        r.headers['X-Accel-Redirect'] = "/dicom/" + filename
        return r
