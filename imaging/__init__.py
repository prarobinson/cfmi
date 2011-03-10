from flask import Flask

app = Flask(__name__)
app.config.from_object('imaging.settings')

from flaskext.sqlalchemy import SQLAlchemy

db = SQLAlchemy(app)

import imaging.views

