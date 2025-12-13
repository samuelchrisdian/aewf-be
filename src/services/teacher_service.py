from src.domain.models import Teacher
from src.repositories.teacher_repo import TeacherRepository

class TeacherService:
    def __init__(self):
        self.repo = TeacherRepository()

    def get_teacher(self, teacher_id: str) -> Teacher:
        return self.repo.get_by_id(teacher_id)

teacher_service = TeacherService()
