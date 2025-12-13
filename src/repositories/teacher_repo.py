from src.domain.models import Teacher, Class
from src.app.extensions import db

class TeacherRepository:
    def get_by_id(self, teacher_id: str) -> Teacher:
        return db.session.query(Teacher).filter(Teacher.teacher_id == teacher_id).first()

    def get_classes_by_teacher(self, teacher_id: str) -> list[Class]:
        return db.session.query(Class).filter(Class.wali_kelas_id == teacher_id).all()
