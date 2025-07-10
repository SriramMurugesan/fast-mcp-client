"""Entry-point that starts the FastAPI server with authentication & DB.

• Imports the existing `client.app` (original code unchanged).
• Imports `auth_setup` – this adds auth routes + /query protection.
• Imports `db_backend_sqlalchemy` – this initialises SQLite tables.

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
