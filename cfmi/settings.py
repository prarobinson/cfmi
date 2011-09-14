import os

## Flask Settings

class DefaultConfig(object):
    SECRET_KEY = 'secret'
    DEBUG = True
    TESTING = False
    SERVER_NAME = 'localhost.devel:5000'

    ## Database Settings
    SQLALCHEMY_DATABASE_URI = \
        'sqlite://'

    SQLALCHEMY_BINDS = {'dicom':
                            'sqlite://'}

    ## Cache settings
    from flaskext.cache import Cache
    cache = Cache()
    CACHE_TYPE = 'simple'

    ## File Paths
    TMP_PATH = '/tmp/'
    BASE_PATH = "/".join(os.path.abspath(__file__).split("/")[:-1])

    ## Imaging Settings
    DICOM_ARCHIVE_FOLDER = BASE_PATH+'/dicom/'
    IMAGING_EMAIL = "imaging@example.com"

    ## Billing Settings
    BILLING_EMAIL = "billing@example.com"

    ## LDAP Settings
    LDAP_ADMIN = None
    LDAP_ADMIN_PASSWD = None
    LDAP_URI = None
    LDAP_USER_DN_TEMPLATE = None

class TestConfig(DefaultConfig):
    TESTING = True
    CSRF_ENABLED = False
    
