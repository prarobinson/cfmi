from formalchemy import FieldSet
from flaskext.wtf import Form, TextField, Required, TextAreaField, FloatField

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

class ProblemRequestForm(Form):
    problem = TextAreaField("Describe the nature of our error:", [Required()])
    duration = FloatField("What is the accurate duration, in hours, of this scan?", [Required()])
