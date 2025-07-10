import pytest


USERNAME = "alice"
PASSWORD = "hashed_pw"
EMAIL = "alice@example.com"


def test_create_and_get_user(auth_db):
    user = auth_db.create_user(USERNAME, PASSWORD, EMAIL)
    assert user.username == USERNAME
    fetched = auth_db.get_user(USERNAME)
    assert fetched is not None
    assert fetched.email == EMAIL


def test_update_user(auth_db):
    auth_db.create_user(USERNAME, PASSWORD, EMAIL)
    new_email = "alice@newmail.com"
    auth_db.update_user(USERNAME, email=new_email)
    updated = auth_db.get_user(USERNAME)
    assert updated.email == new_email


def test_authenticate_user(auth_db):
    auth_db.create_user(USERNAME, PASSWORD, EMAIL)
    assert auth_db.authenticate_user(USERNAME, PASSWORD) is True
    assert auth_db.authenticate_user(USERNAME, "wrong") is False


def test_delete_user(auth_db):
    auth_db.create_user(USERNAME, PASSWORD, EMAIL)
    auth_db.delete_user(USERNAME)
    assert auth_db.get_user(USERNAME) is None
