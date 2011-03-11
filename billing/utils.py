from calendar import monthrange
from datetime import date, timedelta

from cfmi.billing import newsite

## Utility functions that really don't need to crowd up views.py

def total_ytd():
    year_start = date(date.today().year, 7, 1)
    target_scans = newsite.Session.query.filter(
            newsite.Session.sched_start>=year_start).filter(
            newsite.Session.approved==True).filter(
            newsite.Session.cancelled==False).filter(
            newsite.Session.sched_start<=date.today())
    total = sum(float(x.cost()) for x in target_scans)
    return "${0:.2f}".format(total)

def total_last_month():
    today = date.today()
    year = today.year
    month = today.month-1
    total = sum(float(x.cost()) for x in sessions_from_month(year, month))
    return "${0:.2f}".format(total)
            
def active_pis():
    return newsite.User.query.filter(newsite.User.pi_projects!=None).all()

def sessions_from_month(year, month):
    isoday, numdays = monthrange(year, month)
    min_date = date(year, month, 1)
    max_date = date(year, month, numdays)
    return newsite.Session.query.filter(
        newsite.Session.sched_start>=min_date).filter(
        newsite.Session.sched_start<=max_date).filter(
            newsite.Session.approved==True).filter(
            newsite.Session.cancelled==False)

def limit_month(queryset, year, month):
    isoday, numdays = monthrange(year, month)
    min_date = date(year, month, 1)
    max_date = date(year, month, numdays)
    return queryset.filter(newsite.Session.sched_start>=min_date).filter(
        newsite.Session.sched_start<=max_date).filter(
        newsite.Session.approved==True).filter(
            newsite.Session.cancelled==False)

def active_projects():
    return newsite.Project.query.filter(newsite.Project.is_active==True)

def generate_invoices(year, month):
    for project in active_projects():
        ses = sessions_from_month(year, month).filter(
            newsite.Session.project==project).all()
        start_date = date(year, month, 1)
        if len(ses):
            # If there is something to bill on this project,
            # Then generate the cannonical invoice
            if False in (x.is_devel() for x in ses):
                # There are non-development scans
                if not len(newsite.Invoice.query.filter(
                        newsite.Invoice.project==project).filter(
                        newsite.Invoice.date==start_date).all()):
                    # If the invoice exists already, don't bother
                    inv = newsite.Invoice(project, date)
                    newsite.db_session.add(inv)
                    try:
                        newsite.db_session.commit()
                    except:
                        newsite.db_session.rollback()

def due_invoices():
    today = date.today()
    net30 = timedelta(days=30)
    return newsite.Invoice.query.filter(
        newsite.Invoice.reconciled==False).filter(newsite.Invoice.date<today-net30)
