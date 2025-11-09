import os
import sys
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.database import Base, get_db
from app import models
from main import app


def _make_test_session():
    # Use a single in-memory SQLite DB shared across connections
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return engine, TestingSessionLocal


def override_get_db(SessionLocal):
    def _get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    return _get_db


def seed_products(session):
    items = [
        models.Produto(nome="Produto A", preco=10.50, estoque=100),
        models.Produto(nome="Produto B", preco=5.00, estoque=50),
    ]
    session.add_all(items)
    session.commit()
    return items


def create_client_with_db():
    engine, SessionLocal = _make_test_session()
    app.dependency_overrides[get_db] = override_get_db(SessionLocal)
    client = TestClient(app)
    return client, SessionLocal, engine


def cleanup_overrides():
    app.dependency_overrides.clear()
