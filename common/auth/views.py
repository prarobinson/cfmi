from flask import (Module, url_for, redirect, session, flash, g,
                   request, render_template, current_app)

from cfmi.common.database.newsite import User

auth = Module(__name__, name='auth')

@auth.route('/login/', methods = ['GET','POST'])
def login():
    if not g.user:
        if request.method=='POST':
            uname = request.form['username']
            passwd = request.form['password']
            user = User.query.filter(
                User.username==uname).first()
            if user and user.auth(passwd):
                session['user_id'] = user.id
            if current_app.config['TESTING']:
                session['user_id'] = user.id
            else:
                flash('Invalid user/pass')
        else:
            # For method 'GET'
            return render_template('login.html')
    if 'next' in request.args:
        return redirect(request.args['next'])
    else:
        return redirect(url_for('frontend.index'))

@auth.route('/logout/')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out")
    return redirect(url_for('frontend.index'))

