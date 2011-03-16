import os
import unittest
from datetime import datetime, date, timedelta
from time import sleep

from cfmi.imaging import create_app

from cfmi.common.database import dicom, newsite

from cfmi.common.database.dicom import Series, Subject as DicomSubject
from cfmi.common.database.newsite import (
    User, Project, Subject)

class CfmiImagingTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(testing=True)
        self.client = self.app.test_client()
        self.ctx = self.app.test_request_context()
        self.ctx.push()
        dicom.drop_all()
        dicom.create_all()
        newsite.drop_all()
        newsite.create_all()
        admin = User()
        admin.username = 'admin'
        admin.name = 'Admin user'
        admin.permission_level = 3
        newsite.db_session.add(admin)
        newsite.db_session.commit()
        assert admin.id
        nonpi = User()
        nonpi.username = 'nonPI'
        nonpi.name = 'NonPI User'
        nonpi.permission_level = 1
        newsite.db_session.add(nonpi)
        newsite.db_session.commit()
        assert nonpi.id
        pi = User()
        pi.username = 'PI'
        pi.name = 'PI User'
        pi.permission_level = 1
        newsite.db_session.add(pi)
        newsite.db_session.commit()
        assert pi.id
        proj = Project()
        proj.name = "Fancy project"
        proj.pi = pi
        proj.is_active = True
        proj.mri_rate = 500.0
        proj.users.append(nonpi)
        newsite.db_session.add(proj)
        newsite.db_session.commit()
        assert proj.id
        subj = Subject()
        subj.name = "SUBJ01"
        subj.project = proj
        newsite.db_session.add(subj)
        newsite.db_session.commit()
        assert subj.id
        dsubj = DicomSubject()
        dsubj.id = "1.1.1.1.1.11.1"
        dsubj.name = "SUBJ01"
        dicom.db_session.add(dsubj)
        dicom.db_session.commit()
        assert dsubj.id
        ser = dicom.Series()
        ser.id = "2.2.2.2"
        ser.study_id = "1.1.1.1.1"
        ser.date = date.today()
        ser.subject = dsubj
        dicom.db_session.add(ser)
        dicom.db_session.commit()
        assert ser.id

    def tearDown(self):
        newsite.db_session.remove()
        newsite.drop_all()        
        dicom.db_session.remove()
        dicom.drop_all()
        self.ctx.pop()

    def test_can_query_all_objects(self):
        User.query.all()
        Project.query.all()
        Subject.query.all()
        DicomSubject.query.all()
        Series.query.all()

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

if __name__ == "__main__":
    unittest.main()
