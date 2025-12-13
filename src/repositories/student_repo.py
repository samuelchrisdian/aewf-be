from src.domain.models import Student
from src.app.extensions import db

class StudentRepository:
    def get_by_nis(self, nis: str) -> Student:
        return db.session.query(Student).filter(Student.nis == nis).first()

    def create(self, student: Student) -> Student:
        db.session.add(student)
        db.session.commit()
        return student

    def get_by_class_ids(self, class_ids: list[str]) -> list[Student]:
        return db.session.query(Student).filter(Student.class_id.in_(class_ids)).all()
