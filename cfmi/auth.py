import functools

import nis, crypt
import ldap
ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

from flask import (Blueprint, url_for, redirect, session, flash, g,
                   request, render_template, current_app, abort)

from cfmi.database.newsite import (User, Subject, Project, Session, Invoice)
from cfmi.database.dicom import Series
from cfmi.utils import parse_filename

auth = Blueprint('auth', __name__)

def uid_to_dn(uname):
    return current_app.config['LDAP_USER_DN_TEMPLATE'].format(uname)

def ldap_init():
    ipa = ldap.initialize(current_app.config['LDAP_URI'])
    ipa.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
    ipa.set_option(ldap.OPT_X_TLS,ldap.OPT_X_TLS_DEMAND)
    ipa.start_tls_s()
    return ipa

def ldap_auth(uname, password):
    ipa = ldap_init()
    dn = uid_to_dn(uname)
    try: 
        ipa.simple_bind_s(dn, password)
        return True
    except ldap.LDAPError: 
        return False

def nis_auth(uname, password):
    crypt_passwd = nis.cat("passwd.byname")[uname].split(':')[1]
    return crypt.crypt(password, crypt_passwd) == crypt_passwd

def ldap_admin_set_password(uname, password):
    try:
        ipa = ldap_init()
        dn = uid_to_dn(uname)
        ipa.simple_bind_s(current_app.config['LDAP_ADMIN'],
                          current_app.config['LDAP_ADMIN_PASSWD'])
        ipa.passwd_s(dn, '', password)
        print "Set LDAP password for user: {}".format(uname)
    except ldap.LDAPError, e:
        print 'Failed to set LDAP password for user {}: {}'.format(uname, e)

#def nis_change_password(uname, password, new):
#    pass

#def ldap_change_password(uname, password, new):
#    ipa = ldap_init()
#    dn = uid_to_dn(uname)
#    ipa.simple_bind_s(dn, password)
#    ipa.passwd_s(dn, password, new)

def user_auth(user, passwd):
    uname = user.username
    try:
        ldap_success = current_app.config['USE_LDAP_AUTH'] and ldap_auth(uname, passwd)
        nis_success = False
        if not ldap_success:
            nis_success = current_app.config['USE_NIS_AUTH'] and nis_auth(uname, passwd)
    except ldap.SERVER_DOWN:
        ldap_success = False
        print 'Error: Can\'t contact LDAP server'
    except nis.error as e:
        print 'NIS Error: {}'.format(e)
        nis_success = False
    
    if current_app.config['LDAP_MIGRATE_FROM_NIS']:
        if not ldap_success and nis_success:
            ldap_admin_set_password(uname, passwd)
            
    print 'User {} LDAP Login: {}'.format(uname, ldap_success)
    print 'User {} NIS Login: {}'.format(uname, nis_success)
    return ldap_success or nis_success

User.auth = user_auth

#def change_password(user, password, new):
#    if current_app.config['USE_LDAP_AUTH']: ldap_change_password(user, password, new)
#    if current_app.config['USE_NIS_AUTH']: nis_change_password(user, password, new)

@auth.route('/login/', methods = ['GET','POST'])
def login():
    if not g.user:
        if request.method=='POST':
            uname = request.form['username']
            passwd = request.form['password']
            if not uname:
                flash('Invalid user/pass', category='error')
                return render_template('login.html')
            user = User.query.filter(
                User.username==uname).first()
            if user: 
                if user.auth(passwd):
                    session['user_id'] = user.id
                    #if current_app.config['LDAP_URI']:
                    #    if not ldap_auth(uname, passwd):
                            # The users password is different in LDAP we
                            # should set it manually as part of the
                            # migration
                    #        ldap_admin_set_password(uname, passwd)
                elif current_app.config['TESTING']:
                    session['user_id'] = user.id
            else:
                flash('Invalid user/pass', category='error')
        else:
            # For method 'GET'
            return render_template('login.html')
    if 'next' in request.args:
        return redirect(request.args['next'])
    else:
        return redirect('/')

@auth.route('/logout/')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out", category='info')
    return redirect(url_for('.login'))

def authorized_users_only(f):
    @functools.wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        subj_str = None
        project = None
        if g.user.is_superuser():
            return f(*args, **kwargs)
        if 'filename' in kwargs:
            subj_str, exten = parse_filename(kwargs['filename'])
        if 'subject' in kwargs:
            subj_str = kwargs['subject']
        if 'session_id' in kwargs:
            session = Session.query.get(
                kwargs['session_id'])
            if not session: abort(404)
            project = session.project
        if 'invoice_id' in kwargs:
            invoice = Invoice.query.get(
                kwargs['invoice_id'])
            if not invoice: abort(404)
            project = invoice.project
        if 'pi_uname' in kwargs:
            if g.user.username == kwargs['pi_uname']:
                return f(*args, **kwargs)
        if 'series_id' in kwargs:
            subj_str = Series.query.get(
                kwargs['series_id']).subject.name
        if subj_str:
            project = Subject.query.filter(
                Subject.name==subj_str).first().project
        if 'project_id' in kwargs:
            project = Project.get(kwargs['project_id'])
        if project:
            if project.auth(g.user):
                return f(*args, **kwargs)
        abort(403)
    return wrapper

def login_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not g.user:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return wrapper

def superuser_only(f):
    @functools.wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if not g.user.is_superuser():
            abort(403)
        return f(*args, **kwargs)
    return wrapper
