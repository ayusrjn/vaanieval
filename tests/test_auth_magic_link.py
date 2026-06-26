from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import get_settings
from app.db.base import Base
from app.models import MagicLinkToken, User
from app.services.auth_service import request_magic_link


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)()


def test_magic_link_dev_autoprovisions_and_returns_token(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "dev")
    get_settings.cache_clear()
    db = _session()

    try:
        result = request_magic_link(db, "new@example.com")

        assert result.token
        assert result.sent is True
        assert db.scalar(select(User).where(User.email == "new@example.com")) is not None
        assert db.scalar(select(MagicLinkToken)) is not None
    finally:
        db.close()
        get_settings.cache_clear()


def test_magic_link_production_does_not_autoprovision_unknown_email(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    db = _session()

    try:
        result = request_magic_link(db, "unknown@example.com")

        assert result.token is None
        assert result.sent is False
        assert db.scalar(select(User).where(User.email == "unknown@example.com")) is None
        assert db.scalar(select(MagicLinkToken)) is None
    finally:
        db.close()
        get_settings.cache_clear()


def test_magic_link_production_never_exposes_raw_token_for_existing_user(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    db = _session()

    try:
        user = User(email="existing@example.com")
        db.add(user)
        db.commit()

        result = request_magic_link(db, "existing@example.com")

        assert result.token is None
        assert result.sent is False
        assert db.scalar(select(MagicLinkToken).where(MagicLinkToken.user_id == user.id)) is not None
    finally:
        db.close()
        get_settings.cache_clear()
