from src.domain.models import Student
from src.repositories.student_repo import StudentRepository

class StudentService:
    def __init__(self):
        self.repo = StudentRepository()

    def create_student(self, nis: str, name: str, class_id: str) -> Student:
        # Business logic validation could go here
        student = Student(nis=nis, name=name, class_id=class_id)
        return self.repo.create(student)

    def get_student(self, nis: str) -> Student:
        return self.repo.get_by_nis(nis)

    def get_students_by_teacher(self, teacher_id: str) -> list[Student]:
        # This logic involves TeacherRepo as well, or we inject it.
        # But based on prev implementation, we get classes first.
        # Ideally this belongs in a service that orchestrates both or just utilizes repos.
        # For simplicity, I'll instantiate TeacherRepo here or import it.
        from src.repositories.teacher_repo import TeacherRepository
        teacher_repo = TeacherRepository()
        
        classes = teacher_repo.get_classes_by_teacher(teacher_id)
        if not classes:
            return []
            
        class_ids = [c.class_id for c in classes]
        return self.repo.get_by_class_ids(class_ids)

student_service = StudentService()
