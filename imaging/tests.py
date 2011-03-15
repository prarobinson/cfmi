import unittest
from datetime import datetime, date, timedelta
from time import sleep

from cfmi.imaging import create_app

from cfmi.common.database.dicom import (
    Subject as DicomSubject, Series, create_all as create_all_dicom, 
    db_session as db_session_dicom)

from cfmi.common.database.newsite import (
    User, Project, Subject, db_session, create_all)

class CfmiImagingTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(testing=True)
        self.client = self.app.test_client()
        self._ctx = self.app.test_request_context()
        self._ctx.push()
        create_all_dicom()
        create_all()

    def tearDown(self):
        self._ctx.pop()

    def test_can_query_all_objects(self):
        User.query.all()
        Project.query.all()
        Subject.query.all()
        DicomSubject.query.all()
        Series.query.all()

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
        dsubj = DicomSubject()
        dsubj.id = "1.1.1.1.1.11.1"
        dsubj.name = "SUBJ01"
        db_session_dicom.add(dsubj)
        db_session_dicom.commit()
        assert dsubj.id
        ser = Series()
        ser.id = "2.2.2.2"
        ser.study_id = "1.1.1.1.1"
        ser.date = date.today()
        ser.subject = dsubj
        db_session_dicom.add(ser)
        db_session_dicom.commit()
        assert ser.id
        assert admin.is_superuser()
        assert not nock.is_superuser()
        assert not john.is_superuser()
        for user in [admin, nock, john]:
            assert proj.auth(user)
            assert subj.auth(user)
            assert proj in user.get_projects()

if __name__ == "__main__":
    unittest.main()
