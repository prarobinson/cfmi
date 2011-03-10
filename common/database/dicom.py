from sqlalchemy import create_engine
from sqlalchemy.orm import relationship, backref, sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Table, Column, ForeignKey, Integer, String, Boolean, 
                        Numeric, Text, DateTime)

import settings

engine = create_engine(settings.DICOM_DB_STRING, pool_recycle=300)
Session = scoped_session(sessionmaker(bind=engine,autocommit=False,
                                      autoflush=False))
Base = declarative_base()
Base.query = Session.query_property()

## Utility Functions

def cleanup_session():
    Session.remove()

## Models

class DicomSubject(Base):
    __tablename__='imaging_subject'
    id = Column(String(64), primary_key=True)
    name = Column(String(64))

    def get_all_series(self):
        ## This function exists to work around the fact that subject names are
        ## not unique to dicom. This probably introduces a security risk if two
        ## unrealted projects were to choose the same subject nameing scheme
        all_synonyms = DicomSubject.query.filter(DicomSubject.name==self.name).all()
        series_list = []
        for subject in all_synonyms:
            series_list += subject.series_list
        return [[series.id, series.date.strftime("%Y/%m/%d")] for series in series_list]

    def get_series(self):
        return [[series.id, series.date.strftime("%Y/%m/%d")] for series in self.series_list]

    def __repr__(self):
        return "<DicomSubject: {0}".format(self.name)

class DicomSeries(Base):
    __tablename__='imaging_series'
    id = Column(String(64), primary_key=True)
    study_id = Column(String(64))
    date = Column(DateTime)
    subject_id = Column(String(64), 
                           ForeignKey('imaging_subject.id'))
    program_name = Column(String(64))

    subject = relationship(
            DicomSubject, backref=backref('series_list', order_by=date))

    def __repr__(self):
        return "<DicomSeries: {0}".format(self.id)

    def get_path(self):
        return '/'.join(["/exports/raw/dicom/data/cfmi/MR",
                            self.date.strftime("%Y/%m/%d"),
                            self.study_id+".STU",
                            self.id+".SER"])
