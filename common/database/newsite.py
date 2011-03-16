import pam

from sqlalchemy import create_engine
from sqlalchemy.orm import relationship, backref, sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Table, Column, ForeignKey, Integer, String, Boolean, 
                        DateTime, Numeric, Text, Float, Date)

from flask import render_template

Base = declarative_base()

engine = None

db_session = scoped_session(
    lambda: sessionmaker(bind=engine)())

def init_engine(db_string, **kwargs):
    global engine
    engine = create_engine(db_string, **kwargs)
    global Base
    Base.query = db_session.query_property()
    return engine

def create_all():
    Base.metadata.create_all(bind=engine)

def drop_all():
    Base.metadata.drop_all(bind=engine)

users_assoc_table = Table(
    'Projects2Users', Base.metadata,
    Column('User_ID', Integer, 
           ForeignKey('billing_users.id')),
    Column('Project_ID', Integer, 
           ForeignKey('billing_projects.id')))

class User(Base):
    __tablename__ = 'billing_users'
    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, index=True)

    # Optional Biographical Data
    name = Column(String(255), default='')
    email = Column(String(255), default='')
    phone = Column(String(20), default='')
    permission_level = Column(Integer)

    def __repr__(self):
        return "<User: {0}>".format(
            self.name if self.name else self.username)

    def is_superuser(self):
        return True if self.permission_level == 3 else False

    def get_projects(self):
        if self.is_superuser():
            return Project.query.all()
        l = []
        for project in self.projects + self.pi_projects:
            if not project in l: l.append(project)
        return l

    def auth(self, password):
        return pam.authenticate(self.username, password)


class Project(Base):
    __tablename__ = 'billing_projects'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True)
    is_active = Column(Boolean, default=False)
    pi_id = Column(Integer, ForeignKey('billing_users.id'))
    department = Column(String(255))
    institution = Column(String(255))
    address = Column(Text)
    phone = Column(String(255))
    email = Column(String(255))
    rx_num = Column(String(255))
    mri_rate = Column(Numeric)

    pi = relationship(User, backref=backref(
            'pi_projects', order_by=name))
    users = relationship(User, secondary=users_assoc_table, 
                         backref=backref('projects', 
                                         order_by=name))

    def __repr__(self):
        return self.shortname()

    def shortname(self):
        if not self.name:
            return "<Untitled Project>"
        if len(self.name) <= 65:
            return self.name
        return self.name[:65]+"..."

    def get_subjects(self):
        return [subject.name for subject in self.subjects]

    def auth(self, user):
        if user.is_superuser():
            return True
        return user in self.users or self.pi is user


class Subject(Base):
    __tablename__ = 'billing_subjects'
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    project_id = Column(Integer, ForeignKey(
            'billing_projects.id'))

    project = relationship(Project, backref=backref(
            'subjects', order_by=name))

    def __repr__(self):
        return self.name

    def auth(self, user):
        return self.project.auth(user)

class Session(Base):
    __tablename__ = 'billing_sessions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('billing_users.id'))
    sched_start = Column(DateTime)
    sched_end = Column(DateTime)
    approved = Column(Boolean)
    cancelled = Column(Boolean)
    project_id = Column(Integer, 
                        ForeignKey('billing_projects.id'))
    subject_id = Column(Integer, 
                        ForeignKey('billing_subjects.id'))
    start = Column(DateTime)
    end = Column(DateTime)
    notes = Column(Text)

    project = relationship(Project, backref=backref(
            'sessions', order_by=sched_start))
    subject = relationship(Subject, backref=backref(
            'sessions', order_by=sched_start))
    user = relationship(User, backref=backref(
            'sessions', order_by=sched_start))

    def __repr__(self):
        return self.sched_start.strftime("%m/%d/%Y-%H:%M")

    def auth(self, user):
        return self.project.auth(user)

class Problem(Base):
    __tablename__='Problems'
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, 
                        ForeignKey('billing_sessions.id'))
    description = Column(String(255))
    duration = Column(Float)

    session = relationship(
        Session, backref=backref('problem', uselist=False))

    def __repr__(self):
        return "<Problem: %s>" % self.session

    def __init__(self, session=None):
        self.session = session

class Invoice(Base):
    __tablename__='billing_invoices'
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, 
                        ForeignKey('billing_projects.id'))
    date = Column(Date)
    reconciled = Column(Boolean)

    project = relationship(Project, backref=backref('invoices', 
                                                    order_by=date))

    def __repr__(self):
        return "<Invoice: {0}, {1}>".format(
            self.project.shortname, self.date)
