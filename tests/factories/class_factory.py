"""
Class factory for test data generation.
"""
import factory
from src.domain.models import Class
from src.app.extensions import db


class ClassFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory for generating Class test data."""
    
    class Meta:
        model = Class
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = "commit"
    
    class_id = factory.Sequence(lambda n: f"X-IPA-{n}")
    class_name = factory.LazyAttribute(lambda o: f"Kelas {o.class_id}")
    wali_kelas_id = None
