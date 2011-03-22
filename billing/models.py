from calendar import monthrange
from datetime import date, timedelta

from flask import render_template

from cfmi.common.database import newsite
from cfmi.billing.settings import cache

# Methods to support objects in a billing context

def user_invoices(self):
    queryset = Invoice.query.join(Project).filter(Project.pi==self)
    if len(queryset.all()):
        return queryset
    return False

def project_invoice_scans(self, year, month):
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
                 
def project_invoice_total(self, year, month):
    total = 0.0
    for scan in self.invoice_sessions(year, month):
        total += float(scan.cost())
    return "%.2f" % total

def session_is_devel(self):
    if "] devel" in self.project.name.lower():
        return True
    return False

def session_cost(self):
    if self.is_devel():
        return "%.2f" % 0
    quar_rate = float(self.project.mri_rate) / 4
    return "%.2f" % (round(self.duration() / 900) * quar_rate)

def session_duration(self):
    if self.is_corrected():
        return self.problem.duration * 3600
    return (self.billing_end() - self.billing_start()).seconds

def session_dur_hours(self):
    return "%.2f" % round(self.duration() / 3600.0, 2)

def session_billing_start(self):
    if not self.start:
        self.start = self.sched_start
    return min([self.sched_start, self.start])

def session_billing_end(self):
    if not self.end:
        self.end = self.sched_end
    return max([self.sched_end, self.end])

def session_is_corrected(self):
    if self.problem:
        return True
    return False

def session_dur_actual(self):
    return "%.2f" % round(
        (self.billing_end() - self.billing_start(
                )).seconds / 3600.0, 2)

def session_billing_comment(self):
    return self.problem.description

def invoice_sessions(self):
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

def invoice_render(self):
    return render_template('invoice.html', 
                           invoice=self,
                           total=self.total())

@cache.memoize(600)
def invoice_total(self):
    total = sum(float(scan.cost()) for scan in self.sessions())
    return "%.2f" % total

# Add the methods, and make the objects easy to import

User = newsite.User
User.invoices = user_invoices

Project = newsite.Project
Project.invoice_scans = project_invoice_scans
Project.invoice_total = project_invoice_total

Session = newsite.Session
Session.is_devel = session_is_devel
Session.cost = session_cost
Session.duration = session_duration
Session.dur_hours = session_dur_hours
Session.billing_start = session_billing_start
Session.billing_end = session_billing_end
Session.is_corrected = session_is_corrected
Session.dur_actual = session_dur_actual
Session.billing_comment = session_billing_comment

Problem = newsite.Problem

Invoice = newsite.Invoice
Invoice.sessions = invoice_sessions
Invoice.render = invoice_render
Invoice.total = invoice_total

Subject = newsite.Subject

db_session = newsite.db_session

Base = newsite.Base

engine = newsite.engine
