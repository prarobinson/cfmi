#! /usr/bin/env python

from flaskext.testing import TestCase as Base

from cfmi import create_app, db

class TestCase(Base):

    def create_app(self):
        app = create_app(config="cfmi.test_settings")
        print app.config['SQLALCHEMY_DATABASE_URI']
        return app

    def setUp(self):
        db.create_all()
        pass
    
    def tearDown(self):
        db.session.remove()
        #db.drop_all()

class TestViews(TestCase):

    def test_index(self):
        r = self.client.get('/')
        print self.app.config['SQLALCHEMY_DATABASE_URI']
        assert r.status_code == 200
