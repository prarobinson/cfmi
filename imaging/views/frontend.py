import os

from flask import (send_file, render_template, url_for, abort, 
                   make_response, Module, current_app)

from cfmi.common.auth.decorators import (login_required,
                                         authorized_users_only)

from cfmi.imaging.utils import make_archive, find_series_or_404                                       

frontend = Module(__name__)

# Views
@frontend.route('/')
@login_required
def index():
    return render_template("layout.html") 

@frontend.route('/download/<filename>', methods=['GET','HEAD'])
@authorized_users_only
def download(filename):
    """ get_dicom

    Queue the creation of an archive containing all subject dicom
    files and redirect to the eventual location.

    The heavy lifting is does by the dataserver component that lives
    in dataserver.py

    """
    if not os.path.exists(current_app.config['DICOM_ARCHIVE_FOLDER']+filename):
        # The file doesn't exist, lets start making it
        return make_archive(filename)
    if os.stat(current_app.config['DICOM_ARCHIVE_FOLDER']+filename)[6] == 0:
        # The file exits but is 0 bytes, the dataserver is working 
        # on it already, send them to the waiting page
        return render_template("processing.html", url=url_for(
                'download', filename=filename))

    # If we've made it this far, we're ready to send the file
    if not current_app.config["DEBUG"]:
        # Use nginx for the heavy lifting on the prod setup
        r = make_response()
        r.headers['Content-Disposition'] = "attachment"
        r.headers['X-Accel-Redirect'] = "/dicom/" + filename
        return r
    else:
        return send_file(
            current_app.config['DICOM_ARCHIVE_FOLDER']+filename, 
            as_attachment=True)

@frontend.route('/download/<filename>/ready')
@authorized_users_only
def file_ready(filename):
    if not os.path.exists(current_app.config['DICOM_ARCHIVE_FOLDER']+filename):
        abort(404)
    if not os.stat(current_app.config['DICOM_ARCHIVE_FOLDER']+filename)[6]:
        abort(404)
    return render_template("processing.html", url=url_for(
                'download', filename=filename))

