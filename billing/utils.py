from calendar import monthrange
from datetime import date, timedelta

from cfmi.billing.settings import cache
from cfmi.billing.models import User, Session, Project, Invoice, Problem

## Business logic that doesn't need to crowd up the views

@cache.memoize(2592000)
def fiscal_year(year=None):
    if year:
        year_start = date(year - 1, 7, 1)
        year_end = date(year, 6, 30)
    else:
        year = date.today().year if date.today().month >= 7 else date.today().year-1
        year_end = date.today()
        year_start = date(year, 7, 1)
    target_scans = Session.query.filter(
            Session.sched_start>=year_start).filter(
            Session.approved==True).filter(
            Session.cancelled==False).filter(
            Session.sched_start<=year_end)
    total = sum(float(x.cost()) for x in target_scans)       
    return "${0:.2f}".format(total)

def total_last_month():
    today = date.today()
    year = today.year
    month = today.month-1
    return "${0:.2f}".format(month_total(year, month))

@cache.memoize(86400)
def month_total(year, month):
    total = sum(float(x.cost()) for x in sessions_from_month(year, month))
    return total

def sessions_from_month(year, month):
    isoday, numdays = monthrange(year, month)
    min_date = date(year, month, 1)
    max_date = date(year, month, numdays)
    return Session.query.filter(
        Session.sched_start>=min_date).filter(
        Session.sched_start<=max_date).filter(
            Session.approved==True).filter(
            Session.cancelled==False)

def limit_month(queryset, year, month):
    isoday, numdays = monthrange(year, month)
    min_date = date(year, month, 1)
    max_date = date(year, month, numdays)
    if not queryset.first().__class__ is Session:
        queryset = queryset.join(Session)
    return queryset.filter(Session.sched_start>=min_date).filter(
        Session.sched_start<=max_date).filter(
        Session.approved==True).filter(
            Session.cancelled==False)

def active_projects(year, month):
    return limit_month(Project.query, year, month)

# Cached for a month, since it is expensive and changes monthly
@cache.cached(2592000, key_prefix='gchart_ytd')
def gchart_ytd_url():
    months = {1: 'Jan',
              2: 'Feb',
              3: 'Mar',
              4: 'Apr',
              5: 'May',
              6: 'Jun',
              7: 'Jul',
              8: 'Aug',
              9: 'Sep',
              10: 'Oct',
              11: 'Nov',
              12: 'Dec'}

    today = date.today()
    mon = []
    for i in range(12):
        mon.append((today.month - i if today.month - i >= 1 else today.month - i +12, 
                    today.year if today.month - i >= 1 else today.year-1))
    mon.reverse()
    labels = [months[i[0]] for i in mon]
    totals = [str(round(month_total(i[1],i[0]))/1000) for i in mon]
    src = 'http://chart.apis.google.com/chart?chxl=1:|'
    src += '|'.join(labels) 
    src += '&chxr=0,0,100000|1,0,12&chxt=y,x&chbh=a&chs=463x400&cht=bvg&chco=CCCEFF&chd=t:'
    src += ','.join(totals)
    return src
    
