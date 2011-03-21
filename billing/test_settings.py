import os

from flaskext.cache import Cache

## Billing App Settings

DICOM_DB_STRING = \
    'sqlite:///'

NEWSITE_DB_STRING = \
    'sqlite://'

## Flask Settings

SECRET_KEY = 'testing'
DEBUG = True


## File Paths
BASE_PATH = "/".join(os.path.abspath(__file__).split("/")[:-1])
TEMPLATE_PATHS = [BASE_PATH+"/templates"]

## Email Settings
EMAIL_FROM = "billing@cfmi.georgetown.edu"
EMAIL_REPLY_TO = "sn253@georgetown.edu"


## URL Settings
URL_BASE = "http://localhost:5000/"
ARCHIVE_DOWNLOAD_URL = URL_BASE + "download/"

## Cache settings

cache = Cache()
CACHE_TYPE = 'simple'
