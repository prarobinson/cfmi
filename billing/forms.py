from formalchemy import FieldSet

from cfmi.billing import newsite

class SessionForm(FieldSet):
    def __init__(self):
        FieldSet.__init__(self, newsite.Session)
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
        FieldSet.__init__(self, newsite.Problem)
        self.configure(exclude=[self['session']])
