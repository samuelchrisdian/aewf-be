"""
Teacher factory for test data generation.
"""
import factory
from src.domain.models import Teacher
from src.app.extensions import db


class TeacherFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory for generating Teacher test data."""
    
    class Meta:
        model = Teacher
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = "commit"
    
    teacher_id = factory.Sequence(lambda n: f"T{n:03d}")
    name = factory.Faker("name")
    role = "Teacher"


class WaliKelasFactory(TeacherFactory):
    """Factory for generating Wali Kelas (homeroom teacher) test data."""
    role = "Wali Kelas"
