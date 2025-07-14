
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from fastapi.responses import JSONResponse

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "changeme-super-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24  # 24 hours

USERS_FILE = Path(__file__).with_name("users.json")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

auth_router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")



class User(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    hashed_password: str


class UserCreate(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"




from db_backend_sqlalchemy import (
    create_user as _db_create_user,
    get_user as _db_get_user,
    update_user as _db_update_user,
    delete_user as _db_delete_user,
    SessionLocal as _SessionLocal,
    UserModel as _UserModel,
)


def _load_users() -> dict[str, User]:
    """Return all users from the DB as a dict keyed by username."""
    with _SessionLocal() as db:
        users = db.query(_UserModel).all()
        return {u.username: User(username=u.username, email=u.email, hashed_password=u.hashed_password) for u in users}


def _save_user(user: User):
    """Upsert a user inside the database (helper for register / update)."""
    existing = _db_get_user(user.username)
    if existing:
        _db_update_user(user.username, email=user.email, hashed_password=user.hashed_password)
    else:
        _db_create_user(user.username, user.hashed_password, user.email)


def _save_users(users: dict[str, User]):
    for user in users.values():
        _save_user(user)


def _delete_user(username: str):
    _db_delete_user(username)




def _verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def _create_access_token(data: dict, expires_delta: int = ACCESS_TOKEN_EXPIRE_SECONDS) -> str:
    to_encode = data.copy()
    expire = int(time.time()) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)




def _get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    users = _load_users()
    user = users.get(username)
    if user is None:
        raise credentials_exception
    return user




@auth_router.post("/register", response_model=Token, status_code=201,operation_id="register")
def register(user_in: UserCreate):
    if _db_get_user(user_in.username):
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_pw = _get_password_hash(user_in.password)
    _db_create_user(user_in.username, hashed_pw, user_in.email)

    token = _create_access_token({"sub": user_in.username})
    return Token(access_token=token)


class LoginInput(BaseModel):
    username: str
    password: str


@auth_router.post("/login", response_model=Token, operation_id="login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    

    user_row = _db_get_user(form_data.username)
    if user_row is None or not _verify_password(form_data.password, user_row.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    token = _create_access_token({"sub": user_row.username})
    return Token(access_token=token)


@auth_router.get("/users/me", response_model=User, operation_id="read_users_me")
def read_user_me(current_user: User = Depends(_get_current_user)):
    return current_user


@auth_router.put("/users/me", response_model=User, operation_id="update_user_me")
def update_user_me(update: UserUpdate, current_user: User = Depends(_get_current_user)):
    user_email = update.email if update.email is not None else current_user.email
    new_hashed = _get_password_hash(update.password) if update.password else current_user.hashed_password
    _db_update_user(current_user.username, email=user_email, hashed_password=new_hashed)
    return User(username=current_user.username, email=user_email, hashed_password=new_hashed)


@auth_router.delete("/users/me", status_code=204, operation_id="delete_user_me")
def delete_user_me(current_user: User = Depends(_get_current_user)):
    _delete_user(current_user.username)
    return None


@auth_router.get("/users", response_model=list[User], operation_id="read_users")
def read_users(current_user: User = Depends(_get_current_user)):
    """Retrieve details of all registered users (requires authentication)."""
    return list(_load_users().values())






def _auth_middleware_factory(app: FastAPI):
    """Return middleware function that checks JWT for /query."""

    async def auth_middleware(request: Request, call_next):
        if request.url.path.startswith("/query"):
            auth_header: str | None = request.headers.get("Authorization")
            if not auth_header or not auth_header.lower().startswith("bearer "):
                return _unauthorized()
            token = auth_header.split()[1]
            try:
                _get_current_user(token)  
            except HTTPException:
                return _unauthorized()
        return await call_next(request)

    return auth_middleware


def _unauthorized():
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Not authenticated"},
        headers={"WWW-Authenticate": "Bearer"},
    )




def setup_auth(app: FastAPI):
    """Call once to attach router + middleware to an existing FastAPI `app`."""


    if getattr(app.state, "_auth_setup", False):
        return

    app.include_router(auth_router)
    app.middleware("http")(_auth_middleware_factory(app))

    app.state._auth_setup = True



try:
    from client import app as _existing_app

    setup_auth(_existing_app)
except ModuleNotFoundError:
    pass
