from cfmi import db

from cfmi.database.dicom import Series, DicomSubject

users_assoc_table = db.Table(
    'Projects2Users', db.Model.metadata,
    db.Column('User_ID', db.Integer, 
           db.ForeignKey('billing_users.id')),
    db.Column('Project_ID', db.Integer, 
           db.ForeignKey('billing_projects.id')))

class User(db.Model):
    __tablename__ = 'billing_users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, index=True)

    # Optional Biographical Data
    name = db.Column(db.String(255), default='')
    email = db.Column(db.String(255), default='')
    phone = db.Column(db.String(20), default='')
    permission_level = db.Column(db.Integer)

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

    def get_subjects(self):
        l = []
        for project in self.get_projects():
            for subject in project.get_subjects():
                if not subject in l: l.append(subject)
        return l

class Project(db.Model):
    __tablename__ = 'billing_projects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True)
    is_active = db.Column(db.Boolean, default=False)
    pi_id = db.Column(db.Integer, db.ForeignKey('billing_users.id'))
    department = db.Column(db.String(255))
    institution = db.Column(db.String(255))
    address = db.Column(db.Text)
    phone = db.Column(db.String(255))
    email = db.Column(db.String(255))
    rx_num = db.Column(db.String(255))
    mri_rate = db.Column(db.Numeric)

    pi = db.relationship(User, backref=db.backref(
            'pi_projects', order_by=name))
    users = db.relationship(User, secondary=users_assoc_table, 
                         backref=db.backref('projects', 
                                         order_by=name))

    def __repr__(self):
        return self.shortname()

    def shortname(self, limit=55):
        if not self.name:
            return "<Untitled Project>"
        if len(self.name) <= limit:
            return self.name
        return self.name[:limit-3]+"..."

    def auth(self, user):
        if user.is_superuser():
            return True
        return user in self.users or self.pi is user


class Subject(db.Model):
    __tablename__ = 'billing_subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    project_id = db.Column(db.Integer, db.ForeignKey(
            'billing_projects.id'))

    project = db.relationship(Project, backref=db.backref(
            'subjects', order_by=name))

    def __repr__(self):
        return self.name

    def auth(self, user):
        return self.project.auth(user)

    def get_series(self):
        series = [series for session in self.sessions for series in session.series]
        if not series:
            print "Session search failed, failing back to string search"
            print self.sessions
            series = Series.query.join(DicomSubject).filter(DicomSubject.name==self.name).all()
        return series

class Session(db.Model):
    __tablename__ = 'billing_sessions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('billing_users.id'))
    sched_start = db.Column(db.DateTime)
    sched_end = db.Column(db.DateTime)
    approved = db.Column(db.Boolean)
    cancelled = db.Column(db.Boolean)
    project_id = db.Column(db.Integer, 
                        db.ForeignKey('billing_projects.id'))
    subject_id = db.Column(db.Integer, 
                        db.ForeignKey('billing_subjects.id'))
    start = db.Column(db.DateTime)
    end = db.Column(db.DateTime)
    notes = db.Column(db.Text)

    project = db.relationship(Project, backref=db.backref(
            'sessions', order_by=sched_start))
    subject = db.relationship(Subject, backref=db.backref(
            'sessions', order_by=sched_start))
    user = db.relationship(User, backref=db.backref(
            'sessions', order_by=sched_start))

    def __repr__(self):
        return self.sched_start.strftime("%m/%d/%Y-%H:%M")

    def auth(self, user):
        return self.project.auth(user)

    def duration(self):
        return (self.end - self.start).seconds

    @property
    def series(self):
        if self.cancelled or not self.start:
            return None
        if not self.end:
            self.end = self.sched_end
        series = Series.query.filter(Series.date>=self.start).filter(
            Series.date<=self.end).order_by(Series.date).first()
        if not series:
                return []
        return Series.query.filter(Series.study_id==series.study_id).all()

class Problem(db.Model):
    __tablename__='Problems'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, 
                        db.ForeignKey('billing_sessions.id'))
    description = db.Column(db.String(255))
    duration = db.Column(db.Float)

    session = db.relationship(
        Session, backref=db.backref('problem', uselist=False))

    def __repr__(self):
        return "<Problem: %s>" % self.session

    def __init__(self, session=None):
        self.session = session

class Invoice(db.Model):
    __tablename__='billing_invoices'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, 
                        db.ForeignKey('billing_projects.id'))
    date = db.Column(db.Date)
    reconciled = db.Column(db.Boolean, default=False)
    sent = db.Column(db.Boolean, default=False)

    project = db.relationship(Project, backref=db.backref('invoices', 
                                                    order_by=date))

    def __repr__(self):
        return "<Invoice: {0}, {1}>".format(
            self.project.shortname, self.date)
