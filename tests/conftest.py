import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("RATE_LIMITING_ENABLED", "false")

from common.config import reset_settings_cache  # noqa: E402

reset_settings_cache()

from common.database import Base, SessionLocal, engine  # noqa: E402
from services.bookings.app import app as bookings_app  # noqa: E402
from services.reviews.app import app as reviews_app  # noqa: E402
from services.rooms.app import app as rooms_app  # noqa: E402
from services.users.app import app as users_app  # noqa: E402


@pytest.fixture(autouse=True, scope="function")
def _create_test_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session() -> Generator:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def users_client() -> Generator[TestClient, None, None]:
    with TestClient(users_app) as client:
        yield client


@pytest.fixture()
def rooms_client() -> Generator[TestClient, None, None]:
    with TestClient(rooms_app) as client:
        yield client


@pytest.fixture()
def bookings_client() -> Generator[TestClient, None, None]:
    with TestClient(bookings_app) as client:
        yield client


@pytest.fixture()
def reviews_client() -> Generator[TestClient, None, None]:
    with TestClient(reviews_app) as client:
        yield client
