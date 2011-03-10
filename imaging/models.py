from imaging import db

class DicomSubject(db.Model):
    __tablename__='imaging_subject'
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(64))

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

class Series(db.Model):
    __tablename__='imaging_series'
    id = db.Column(db.String(64), primary_key=True)
    study_id = db.Column(db.String(64))
    date = db.Column(db.DateTime)
    subject_id = db.Column(db.String(64), 
                           db.ForeignKey('imaging_subject.id'))
    program_name = db.Column(db.String(64))

    subject = db.relationship(
            DicomSubject, backref=db.backref('series_list', order_by=date))

    def get_path(self):
        return '/'.join(["/exports/raw/dicom/data/cfmi/MR",
                            self.date.strftime("%Y/%m/%d"),
                            self.study_id+".STU",
                            self.id+".SER"])
