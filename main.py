"""
Run with:
    python main.py
or
    uvicorn main:app --reload
"""
from __future__ import annotations

import os

from client import app  # existing FastAPI application

import auth_setup  # side-effect: attach auth & middleware
import db_backend_sqlalchemy  # noqa: F401 – ensure tables are created

from fastapi import Depends
from fastapi_mcp import FastApiMCP, AuthConfig
import auth_setup as auth  # alias for clarity


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

mcp = FastApiMCP(
    app,
    include_operations=[
        # Auth operations
        "register",
        "login",
        "read_users_me",
        "update_user_me",
        "delete_user_me",
        "read_users",
        "read_user",

    ],
    auth_config=AuthConfig(
        dependencies=[Depends(auth._get_current_user)],
    ),
)