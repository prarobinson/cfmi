from formalchemy import FieldSet

from cfmi.billing.models import Session, Problem

class SessionForm(FieldSet):
    def __init__(self):
        FieldSet.__init__(self, Session)
        self.configure(options=[
                self.sched_start.label("Scheduled Start"),
                self.sched_end.label("Scheduled End"),
                self.approved.label("Approved?"),
                self.cancelled.label("Cancelled?"),
                self.start.label("Actual Start"),
                self.end.label("Actual End"),
                self.notes.label("Log").textarea()], exclude=[
                self.problem])

class ROSessionForm(SessionForm):
    def __init__(self):
        SessionForm.__init__(self)
        self.configure(readonly=True)

class ProblemForm(FieldSet):
    def __init__(self):
        FieldSet.__init__(self, Problem)
        self.configure(exclude=[self['session']])
