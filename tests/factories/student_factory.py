"""
Student factory for test data generation.
"""
import factory
from src.domain.models import Student
from src.app.extensions import db


class StudentFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory for generating Student test data."""
    
    class Meta:
        model = Student
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = "commit"
    
    nis = factory.Sequence(lambda n: f"2024{n:04d}")
    name = factory.Faker("name")
    class_id = factory.LazyAttribute(lambda o: "X-IPA-1")
    parent_phone = factory.Faker("phone_number")
    is_active = True


class InactiveStudentFactory(StudentFactory):
    """Factory for generating inactive Student test data."""
    is_active = False
