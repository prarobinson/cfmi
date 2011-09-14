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
    IMAGING_EMAIL = "imaging@cfmi.georgetown.edu"

    ## Billing Settings
    BILLING_EMAIL = "cfmiadmin@georgetown.edu"

    ## LDAP Settings
    LDAP_ADMIN = ""
    LDAP_ADMIN_PASSWD = ""
    LDAP_URI = "ldap://localhost"
    LDAP_USER_DN_TEMPLATE = \
        "uid={},cn=accounts,dc=domain,dc=com"

class TestConfig(DefaultConfig):
    TESTING = True
    CSRF_ENABLED = False
    
