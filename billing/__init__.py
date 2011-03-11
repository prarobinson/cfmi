from flask import Flask

app = Flask(__name__)
app.config.from_object('cfmi.billing.settings')

from cfmi.common.database import Newsite
newsite = Newsite(app=app)

from cfmi.common.cfmiauth import Cfmiauth
cfmiauth = Cfmiauth(app, newsite)

import cfmi.billing.views
import cfmi.billing.api
