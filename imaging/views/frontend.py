from flask import (send_file, render_template, url_for, abort, 
                   make_response, Module, current_app, request)

from cfmi.common.auth.decorators import (login_required,
                                         authorized_users_only)

from cfmi.imaging.utils import make_archive, find_series_or_404, file_ready                                       

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
    
    if file_ready(filename):
        return sendfile(filename)
    else:
        ## Hijack HEAD requests to check status, if the file is ready
        if request.method == 'HEAD':
            abort(404)
        return render_template("processing.html", url=url_for(
                'download', filename=filename))

def sendfile(filename):
    if current_app.config["DEBUG"]:
        # Use flask during development
        print "trying to sendfile"
        return send_file(
            current_app.config['DICOM_ARCHIVE_FOLDER']+filename, 
            as_attachment=True)
    else:
        # Use nginx for the heavy lifting on the prod setup
        r = make_response()
        r.headers['Content-Disposition'] = "attachment"
        r.headers['X-Accel-Redirect'] = "/dicom/" + filename
        return r




