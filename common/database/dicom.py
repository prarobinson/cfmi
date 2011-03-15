from sqlalchemy import create_engine
from sqlalchemy.orm import relationship, backref, sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Table, Column, ForeignKey, Integer, String, Boolean, 
                        Numeric, Text, DateTime)

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


class Subject(Base):
    __tablename__='imaging_subject'
    id = Column(String(64), primary_key=True)
    name = Column(String(64))

    def get_all_series(self):
    ## This function exists to work around the fact that
    ## subject names are not unique to dicom. This probably
    ## introduces a security risk if two unrealted projects
    ## were to choose the same subject nameing scheme
        all_synonyms = Subject.query.filter(
            Subject.name==self.name).all()
        series_list = []
        for subject in all_synonyms:
            series_list += subject.series_list
        return [[series.id, 
                 series.date.strftime(
                    "%Y/%m/%d")] for series in series_list]

    def get_series(self):
        return [[series.id, series.date.strftime(
                    "%Y/%m/%d")] for series in self.series_list]

    def __repr__(self):
        return "<DicomSubject: {0}".format(self.name)

class Series(Base):
    __tablename__='imaging_series'
    id = Column(String(64), primary_key=True)
    study_id = Column(String(64))
    date = Column(DateTime)
    subject_id = Column(String(64), 
                        ForeignKey('imaging_subject.id'))
    program_name = Column(String(64))

    subject = relationship(
        Subject, backref=backref('series_list', order_by=date))

    def __repr__(self):
        return "<DicomSeries: {0}".format(self.id)

    def get_path(self):
        return '/'.join(["/exports/raw/dicom/data/cfmi/MR",
                         self.date.strftime("%Y/%m/%d"),
                         self.study_id+".STU",
                         self.id+".SER"])
