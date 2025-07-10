"""SQLAlchemy backend for user authentication storage.
Creates a lightweight SQLite DB (default: users.db) with a `users` table.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

# ---------------------------------------------------------------------------
# DATABASE INITIALISATION
# ---------------------------------------------------------------------------

POSTGRES_URL = os.getenv(
    "POSTGRES_URL",
    "postgresql+psycopg2://postgres.gjisahaenkruawxhntkb:8PIfilU6x82HE7bq@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require&supa=base-pooler.x",
)
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

url_parts = urlsplit(POSTGRES_URL)
if url_parts.scheme.startswith("postgresql"):
    # Sanitize the URL: remove unknown query params (e.g., 'supa') that psycopg2 rejects.
    qs = dict(parse_qsl(url_parts.query))
    allowed_params = {k: v for k, v in qs.items() if k in {"sslmode", "application_name"}}
    cleaned_query = urlencode(allowed_params)
    DB_URL = urlunsplit((url_parts.scheme, url_parts.netloc, url_parts.path, cleaned_query, url_parts.fragment))
else:
    # For other schemes (e.g., sqlite for tests), keep the URL untouched.
    DB_URL = POSTGRES_URL

# For PostgreSQL, no special SQLite connect_args are needed
engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)


# Create tables if they do not exist
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# CRUD HELPERS
# ---------------------------------------------------------------------------

def _get_session() -> Session:
    return SessionLocal()


def create_user(username: str, hashed_password: str, email: Optional[str] = None):
    with _get_session() as db:
        user = UserModel(username=username, hashed_password=hashed_password, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


def get_user(username: str) -> Optional[UserModel]:
    with _get_session() as db:
        try:
            return db.query(UserModel).filter(UserModel.username == username).one()
        except NoResultFound:
            return None


def update_user(username: str, *, email: Optional[str] = None, hashed_password: Optional[str] = None):
    with _get_session() as db:
        user = db.query(UserModel).filter(UserModel.username == username).first()
        if not user:
            return None
        if email is not None:
            user.email = email
        if hashed_password is not None:
            user.hashed_password = hashed_password
        db.commit()
        db.refresh(user)
        return user


def delete_user(username: str):
    with _get_session() as db:
        user = db.query(UserModel).filter(UserModel.username == username).first()
        if user:
            db.delete(user)
            db.commit()


def authenticate_user(username: str, hashed_password: str) -> bool:
    user = get_user(username)
    if not user:
        return False
    return user.hashed_password == hashed_password
