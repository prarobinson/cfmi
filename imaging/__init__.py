import settings
from flask import Flask

app = Flask(__name__)
app.config.from_object('cfmi.imaging.settings')

from cfmi.common.database import Dicom
dicom = Dicom(app=app)

from cfmi.common.database import Newsite
newsite = Newsite(app=app)

from cfmi.common.cfmiauth import Cfmiauth
cfmiauth = Cfmiauth(app, newsite, dicom)

import cfmi.imaging.views

