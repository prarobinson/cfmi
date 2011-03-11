import pam
from calendar import monthrange
from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import relationship, backref, sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Table, Column, ForeignKey, Integer, String, Boolean, 
                        DateTime, Numeric, Text, Float, Date)

from flask import render_template

Base = declarative_base()

class Newsite:
    def __init__(self, app=None, db_string=None):
        if not app or db_string:
            raise RuntimeError("Either a Flask app or db_string must be provided")
        if app:
            self.app = app
            self.app.config.setdefault('NEWSITE_DB_STRING', 'sqlite:///')
            engine = create_engine(app.config['NEWSITE_DB_STRING'],
                                   pool_recycle=300)
        if db_string:
            engine = create_engine(db_string,
                                   pool_recycle=300)

        self.db_session = scoped_session(sessionmaker(bind=engine,autocommit=False,
                                      autoflush=False))
       
        Base.query = self.db_session.query_property()

        @app.after_request
        def after_request(response):
            self.db_session.remove()
            return response

        self.User = User
        self.Project = Project
        self.Subject = Subject
        self.Session = Session
        self.Problem = Problem
        self.Invoice = Invoice

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

    def invoices(self):
        queryset = Invoice.query.join(Project).filter(Project.pi==self)
        if len(queryset.all()):
            return queryset
        return False


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
        return user in self.users or self.pi is user

    def invoice_scans(self, year, month):
        isoday, numdays = monthrange(year, month)
        mindate = date(year, month, 1)
        maxdate = mindate + timedelta(days=numdays)
        return Session.query.filter(
            Session.project==self).filter(
            Session.sched_start>=mindate).filter(
                Session.sched_end<=maxdate).filter(
                Session.approved==True).filter(
                    Session.cancelled==False).order_by(
                    Session.sched_start).all()

    def invoice_scans_total(self, year, month):
        total = 0.0
        for scan in self.invoice_scans(year, month):
            total += float(scan.cost())
        return "%.2f" % total


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

    def is_devel(self):
        if "] devel" in self.project.name.lower():
            return True
        return False

    def cost(self):
        if self.is_devel():
            return "%.2f" % 0
        quar_rate = float(self.project.mri_rate) / 4
        return "%.2f" % (round(self.duration() / 900) * quar_rate)

    def duration(self):
        if self.is_corrected():
            return self.problem.duration * 3600
        return (self.billing_end() - self.billing_start()).seconds

    def dur_hours(self):
        return "%.2f" % round(self.duration() / 3600.0, 2)

    def billing_start(self):
        if not self.start:
            self.start = self.sched_start
        return min([self.sched_start, self.start])

    def billing_end(self):
        if not self.end:
            self.end = self.sched_end
        return max([self.sched_end, self.end])

    def is_corrected(self):
        if self.problem:
            return True
        return False

    def dur_actual(self):
        return "%.2f" % round(
            (self.billing_end() - self.billing_start(
                    )).seconds / 3600.0, 2)

    def billing_comment(self):
        return self.problem.description


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

    def scans(self):
        """ Invoice.sessions(): Returns all trackable sesion for
        the invoice period
        """

        isoday, numdays = monthrange(self.date.year, self.date.month)
        mindate = date(self.date.year, self.date.month, 1)
        maxdate = mindate + timedelta(days=numdays)
        return Session.query.filter(
            Session.project==self.project).filter(
            Session.sched_start>=mindate).filter(
                Session.sched_end<=maxdate).filter(
                Session.approved==True).filter(
                    Session.cancelled==False).order_by(
                    Session.sched_start).all()

    def render_html(self):
        return render_template('invoice.html', 
                               invoice=self,
                                   total=self.total())

    def render_tex(self):
        return render_template('invoice.tex', 
                               sessions=self.scans(),
                               pi=self.project.pi, date=self.date,
                               total=self.total())

    def render_pdf(self):
        tex = self.render_tex()
        path = '/tmp/invoice-%s_%s-%s' % (
            self.project.pi, self.project[:-3], month, year)
        tmpfile = open(path+'.tex', 'w')
        tmpfile.write(tex)
        tmpfile.close()
        r = call(['pdflatex', path+'.tex'], cwd='/tmp/')
        path = path+'.pdf'
        return send_file(path, as_attachment=True)

    def total(self):
        total = sum(float(scan.cost()) for scan in self.scans())
        return "%.2f" % total
