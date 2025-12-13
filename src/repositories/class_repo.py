from src.domain.models import Class
from src.app.extensions import db

class ClassRepository:
    def get_by_id(self, class_id: str) -> Class:
        return db.session.query(Class).filter(Class.class_id == class_id).first()
