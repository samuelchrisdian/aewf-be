import pytest
from app import app
from src.db_config import Base, engine, SessionLocal

@pytest.fixture(scope="session")
def test_client():
    app.config["TESTING"] = True
    # In a real scenario, use a separate test DB
    # app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:" 
    
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
