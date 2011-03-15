import unittest
from datetime import datetime, date, timedelta
from time import sleep

from cfmi.billing import create_app
from cfmi.billing.models import (User, Project, Invoice, Session, Subject,
                                 Problem, db_session)
from cfmi.common.database.newsite import create_all

class CfmiBillingTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(testing=True)
        self.client = self.app.test_client()
        self._ctx = self.app.test_request_context()
        self._ctx.push()
        create_all()

    def tearDown(self):
        self._ctx.pop()

    def test_can_query_all_objects(self):
        User.query.all()
        Project.query.all()
        Invoice.query.all()
        Session.query.all()
        Problem.query.all()

    def test_create_models(self):
        admin = User()
        admin.username = 'admin'
        admin.name = 'Admin user'
        admin.permission_level = 3
        db_session.add(admin)
        db_session.commit()
        assert admin.id
        nock = User()
        nock.username = 'nock'
        nock.name = 'Shawn Nock'
        nock.permission_level = 1
        db_session.add(nock)
        db_session.commit()
        assert nock.id
        john = User()
        john.username = 'johnvm'
        john.name = 'John VanMeter'
        john.permission_level = 1
        db_session.add(john)
        db_session.commit()
        assert john.id
        proj = Project()
        proj.name = "Fancy project"
        proj.pi = john
        proj.is_active = True
        proj.mri_rate = 500.0
        proj.users.append(nock)
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
        sess.user = nock
        sess.sched_start = datetime.now()
        sess.sched_end = datetime.now() + timedelta(minutes=60)
        sess.project = proj
        sess.subject = subj
        db_session.add(sess)
        db_session.commit()
        assert sess.id
        sess2 = Session()
        sess2.user = nock
        sess2.sched_start = datetime.now()
        sess2.sched_end = datetime.now() + timedelta(minutes=60)
        sess2.project = proj
        sess2.subject = subj
        db_session.add(sess2)
        db_session.commit()
        assert sess2.id
        prob = Problem()
        prob.session = sess2
        prob.decription = "this has been adjusted"
        prob.duration = .5
        db_session.add(prob)
        db_session.commit()
        assert prob.id
        assert admin.is_superuser()
        assert not nock.is_superuser()
        assert not john.is_superuser()
        for user in [admin, nock, john]:
            assert proj.auth(user)
            assert subj.auth(user)
            assert sess.auth(user)
            assert proj in user.get_projects()
        assert float(sess.cost()) == float(proj.mri_rate)
        assert float(sess.cost())/2 == float(sess2.cost())
        assert sess2.is_corrected()

if __name__ == "__main__":
    unittest.main()
