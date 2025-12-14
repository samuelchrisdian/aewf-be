import pytest
from dotenv import load_dotenv

load_dotenv()

from app import app
from src.db_config import Base, engine, SessionLocal

@pytest.fixture(scope="session")
def test_client():
    app.config["TESTING"] = True
    # Ensure tests use the same database as the application (Postgres)
    # This matches the behavior of SessionLocal used in repositories
    import os
    if os.environ.get("DATABASE_URL"):
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    
    with app.test_client() as client:
        yield client

@pytest.fixture(scope="function")
def db_session():
    """
    Creates a fresh database session for a test.
    Rolls back transaction after test to keep DB clean.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()
