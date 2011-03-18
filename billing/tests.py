import os
import unittest
from datetime import datetime, date, timedelta
from time import sleep

from flask import session

from cfmi.billing import create_app

from cfmi.common.database.newsite import (
    User, Project, Subject, Invoice, Problem, Session, db_session, 
    create_all, drop_all)

class CfmiImagingTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(testing=True)
        self.client = self.app.test_client()
        self.ctx = self.app.test_request_context()
        self.ctx.push()
        drop_all()
        create_all()
        admin = User()
        admin.username = 'admin'
        admin.name = 'Admin user'
        admin.permission_level = 3
        db_session.add(admin)
        db_session.commit()
        assert admin.id
        nonpi = User()
        nonpi.username = 'nonPI'
        nonpi.name = 'NonPI User'
        nonpi.permission_level = 1
        db_session.add(nonpi)
        db_session.commit()
        assert nonpi.id
        pi = User()
        pi.username = 'PI'
        pi.name = 'PI User'
        pi.permission_level = 1
        db_session.add(pi)
        db_session.commit()
        assert pi.id
        proj = Project()
        proj.name = "Fancy project"
        proj.pi = pi
        proj.is_active = True
        proj.mri_rate = 500.0
        proj.users.append(nonpi)
        db_session.add(proj)
        db_session.commit()
        assert proj.id
        subj = Subject()
        subj.name = "SUBJ01"
        subj.project = proj
        db_session.add(subj)
        db_session.commit()
        assert subj.id
        sess = Session()
        sess.sched_start = datetime.now()
        sess.sched_end = sess.sched_start + timedelta(hours=1)
        sess.proj = proj
        sess.subject = subj
        db_session.add(sess)
        db_session.commit()
        assert sess.id
        sess2 = Session()
        sess2.sched_start = datetime.now()
        sess2.sched_end = sess2.sched_start + timedelta(hours=1)
        sess2.proj = proj
        sess2.subject = subj
        prob = Problem()
        prob.description = "This session is corrected"
        prob.sess = sess2
        prob.duration = 0.5
        db_session.add(sess2)
        db_session.add(prob)
        db_session.commit()
        assert prob.id
        assert sess2.id

    def tearDown(self):
        db_session.remove()
        drop_all()        
        self.ctx.pop()

    def login(self, username, password):
        return self.client.post('/login', data=dict(
                username=username,
                password=password
                ), follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    def test_can_query_all_objects(self):
        User.query.all()
        Project.query.all()
        Subject.query.all()
        Invoice.query.all()
        Session.query.all()
        Problem.query.all()

    def test_user_authorization(self):
        admin = User.query.all()[0]
        nonpi = User.query.filter(User.username=='nonPI').first()
        pi = User.query.filter(User.username=='PI').first()
        proj = Project.query.get(1)
        subj = Subject.query.get(1)
        assert admin.is_superuser()
        assert not nonpi.is_superuser()
        assert not pi.is_superuser()
        for user in [admin, nonpi, pi]:
            assert proj.auth(user)
            assert subj.auth(user)
            assert proj in user.get_projects()

    def test_login_admin(self):
        bob = self.login('admin', 'password')
        print bob.data

if __name__ == "__main__":
    unittest.main()
