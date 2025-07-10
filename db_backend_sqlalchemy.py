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

DB_PATH = os.getenv("AUTH_DB_PATH", "users.db")
DB_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
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
