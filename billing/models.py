from flask import render_template

from calendar import monthrange
from datetime import timedelta, date, datetime

from billing import db

from pam import authenticate

users_assoc_table = db.Table(
    'Projects2Users', db.Model.metadata,
    db.Column('User_ID', db.Integer, 
              db.ForeignKey('billing_projects.id')),
    db.Column('Project_ID', db.Integer, 
              db.ForeignKey('billing_users.id')))

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
        return self.name if self.name else self.username
    
    def auth(self, password):
        return authenticate(self.username, password)
    
    def is_superuser(self):
        return True if self.permission_level == 3 else False

    def invoices(self):
        queryset = Invoice.query.join(Project).filter(Project.pi==self)
        if len(queryset.all()):
            return queryset
        return False

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

    def shortname(self):
        if not self.name:
            return "<Untitled Project>"
        if len(self.name) <= 37:
            return self.name
        return self.name[:37]+"..."

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

class Subject(db.Model):
    __tablename__ = 'billing_subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    project_id = db.Column(db.Integer, 
                           db.ForeignKey('billing_projects.id'))
    
    project = db.relationship(Project, 
                              backref=db.backref('subjects', 
                                                 order_by=name))

    def __repr__(self):
        return self.name

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
    reconciled = db.Column(db.Boolean)
    
    project = db.relationship(Project, backref=db.backref('invoices', 
                                                          order_by=date))
    
    def __init__(self, project, date):
        super(self).__init__(self)
        self.project = project
        self.date = date
        self.reconciled = False

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
        path = '/tmp/invoice-%s_%s-%s' % (self.project.pi, 
                                          self.project[:-3], month, year)
        tmpfile = open(path+'.tex', 'w')
        tmpfile.write(tex)
        tmpfile.close()
        r = call(['pdflatex', path+'.tex'], cwd='/tmp/')
        path = path+'.pdf'
        return send_file(path, as_attachment=True)

    def total(self):
        total = sum(float(scan.cost()) for scan in self.scans())
        return "%.2f" % total
