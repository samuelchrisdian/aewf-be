
import factory
from src.domain.models import User
from src.app.extensions import db

class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = "commit"

    id = factory.Sequence(lambda n: n + 1)
    username = factory.Faker("user_name")
    password_hash = factory.Faker("password")
    role = "admin"
