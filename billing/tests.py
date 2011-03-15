import unittest
from datetime import datetime, date, timedelta
from time import sleep

from cfmi.billing import app
from cfmi.billing.models import (User, Project, Invoice, Session, Subject, 
                                 Problem, Base, db_session, 
                                 engine)

class CfmiBillingTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        Base.metadata.create_all(bind=engine)

    def tearDown(self):
        pass

    def test_can_query_all_objects(self):
        User.query.all()
        Project.query.all()
        Invoice.query.all()
        Session.query.all()
        Problem.query.all()

    def test_create_superuser(self):
        test_user = User()
        test_user.username = 'admin'
        test_user.name = 'Admin user'
        test_user.permission_level = 3
        db_session.add(test_user)
        db_session.commit()
        assert User.query.get(test_user.id).is_superuser()

    def test_create_nock(self):
        test_user = User()
        test_user.username = 'nock'
        test_user.name = 'Shawn Nock'
        test_user.permission_level = 1
        db_session.add(test_user)
        db_session.commit()
        assert not User.query.get(test_user.id).is_superuser()

    def test_create_john(self):
        test_user = User()
        test_user.username = 'johnvm'
        test_user.name = 'John VanMeter'
        test_user.permission_level = 1
        db_session.add(test_user)
        db_session.commit()
        assert not User.query.get(test_user.id).is_superuser()

    def test_project(self):
        proj = Project()
        nock = User.query.filter(User.username=='nock').first()
        john = User.query.filter(User.username=='johnvm').first()
        admin = User.query.filter(User.username=='admin').first()
        proj.name = "Fancy project"
        proj.pi = john
        proj.is_active = True
        proj.mri_rate = 500.0
        db_session.add(proj)
        db_session.commit()
        proj.users.append(nock)
        db_session.add(proj)
        db_session.commit()
        assert proj.pi == john
        assert nock in proj.users
        assert proj in nock.get_projects()
        assert proj in john.get_projects()
        assert proj in admin.get_projects()
        assert proj.auth(nock)
        assert proj.auth(john)

    def test_subject(self):
        proj = Project.query.all()[0]
        subj = Subject()
        subj.name = "SUBJ01"
        subj.project = proj
        db_session.add(subj)
        db_session.commit()
        proj = Project.query.all()[0]
        nock = User.query.filter(User.username=='nock').first()
        john = User.query.filter(User.username=='johnvm').first()
        assert proj
        assert subj.id
        assert subj in proj.subjects
        assert subj.auth(nock)
        assert subj.auth(john)

    def test_session(self):
        proj = Project.query.all()[0]
        nock = User.query.filter(User.username=='nock').first()
        subj = Subject.query.filter(Subject.name=='SUBJ01').first()
        sess = Session()
        sess.user = nock
        sess.sched_start = datetime.now()
        sess.sched_end = datetime.now() + timedelta(minutes=60)
        sess.project = proj
        sess.subject = subj
        db_session.add(sess)
        db_session.commit()
        db_session.refresh(sess)
        assert sess.id
        assert sess.project is proj
        assert sess.subject is subj
        assert sess.user is nock
        assert float(sess.cost()) == float(proj.mri_rate)

    def test_problem(self):
        sleep(1)
        sess = Session.query.all()[0]
        prob = Problem()
        prob.session = sess
        prob.decription = "this has been adjusted"
        prob.duration = 4400
        db_session.add(prob)
        db_session.commit()
        prob = Problem.query.all()[0]
        assert prob
        assert prob.session is sess
        assert float(sess.cost()) > 500
        assert sess.is_corrected()

if __name__ == "__main__":
    unittest.main()
