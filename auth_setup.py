"""
Authentication & user management integration for the existing FastAPI `app` defined in `client.py`.

This module DOES NOT modify any existing application code.  It simply imports the
already-created `app` instance and augments it with:

• User storage backed by a lightweight JSON file (`users.json`).
• Password hashing using passlib (bcrypt).
• JWT authentication using `python-jose`.
• Routes:  
    POST  /register      – create user  
    POST  /login         – obtain JWT token  
    GET   /users/me      – read current user  
    PUT   /users/me      – update current user  
    DELETE /users/me     – delete current user
• Middleware securing the original `/query` endpoint – it can now be
  accessed only with a valid JWT token in the `Authorization: Bearer <token>` header.

Usage
-----
Create a new entry-point (e.g. `main.py`):

```
from client import app  # existing app
import auth_setup  # noqa: F401 – side-effect: augments `app`

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Run with `python main.py` or `uvicorn main:app`.
"""
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

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "changeme-super-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24  # 24 hours

USERS_FILE = Path(__file__).with_name("users.json")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

auth_router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ---------------------------------------------------------------------------
# MODELS
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# STORAGE HELPERS  (very light-weight JSON file storage)
# ---------------------------------------------------------------------------

def _load_users() -> dict[str, User]:
    if USERS_FILE.exists():
        with USERS_FILE.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        return {u["username"]: User(**u) for u in raw}
    return {}


def _save_users(users: dict[str, User]) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    serialisable = [u.dict() for u in users.values()]
    with USERS_FILE.open("w", encoding="utf-8") as f:
        json.dump(serialisable, f, indent=2)


# ---------------------------------------------------------------------------
# SECURITY HELPERS
# ---------------------------------------------------------------------------

def _verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def _create_access_token(data: dict, expires_delta: int = ACCESS_TOKEN_EXPIRE_SECONDS) -> str:
    to_encode = data.copy()
    expire = int(time.time()) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# DEPENDENCIES
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# API ROUTES
# ---------------------------------------------------------------------------

@auth_router.post("/register", response_model=Token, status_code=201)
def register(user_in: UserCreate):
    users = _load_users()
    if user_in.username in users:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_pw = _get_password_hash(user_in.password)
    user = User(username=user_in.username, email=user_in.email, hashed_password=hashed_pw)
    users[user.username] = user
    _save_users(users)

    token = _create_access_token({"sub": user.username})
    return Token(access_token=token)


@auth_router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    users = _load_users()
    user = users.get(form_data.username)
    if user is None or not _verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = _create_access_token({"sub": user.username})
    return Token(access_token=token)


@auth_router.get("/users/me", response_model=User)
def read_user_me(current_user: User = Depends(_get_current_user)):
    return current_user


@auth_router.put("/users/me", response_model=User)
def update_user_me(update: UserUpdate, current_user: User = Depends(_get_current_user)):
    users = _load_users()
    user = users[current_user.username]
    if update.email is not None:
        user.email = update.email
    if update.password is not None:
        user.hashed_password = _get_password_hash(update.password)
    users[user.username] = user
    _save_users(users)
    return user


@auth_router.delete("/users/me", status_code=204)
def delete_user_me(current_user: User = Depends(_get_current_user)):
    users = _load_users()
    users.pop(current_user.username, None)
    _save_users(users)
    return None


# ---------------------------------------------------------------------------
# MIDDLEWARE TO PROTECT /query ENDPOINT
# ---------------------------------------------------------------------------

def _auth_middleware_factory(app: FastAPI):
    """Return middleware function that checks JWT for /query."""

    async def auth_middleware(request: Request, call_next):
        if request.url.path.startswith("/query"):
            # Require Authorization header
            auth_header: str | None = request.headers.get("Authorization")
            if not auth_header or not auth_header.lower().startswith("bearer "):
                return _unauthorized()
            token = auth_header.split()[1]
            try:
                _get_current_user(token)  # will raise on error
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


# ---------------------------------------------------------------------------
# PUBLIC SETUP FUNCTION
# ---------------------------------------------------------------------------

def setup_auth(app: FastAPI):
    """Call once to attach router + middleware to an existing FastAPI `app`."""

    # Avoid double-registration
    if getattr(app.state, "_auth_setup", False):
        return

    app.include_router(auth_router)
    app.middleware("http")(_auth_middleware_factory(app))

    app.state._auth_setup = True


# ---------------------------------------------------------------------------
# INTEGRATE WITH `client.app` WHEN THIS MODULE IS IMPORTED (side-effect)
# ---------------------------------------------------------------------------

try:
    from client import app as _existing_app

    setup_auth(_existing_app)
except ModuleNotFoundError:
    # This module can still be imported standalone, but the user must call
    # `setup_auth(app)` manually after creating their FastAPI instance.
    pass
