from flask import Flask

app = Flask(__name__)
app.config.from_object('billing.settings')

from flaskext.sqlalchemy import SQLAlchemy
db = SQLAlchemy(app)

import billing.views
