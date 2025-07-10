from __future__ import annotations

import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

import client
from client import app
import auth_setup  # sets up auth middleware
import db_backend_sqlalchemy  # sets up DB

from fastapi import Depends
from fastapi_mcp import FastApiMCP, AuthConfig
import auth_setup as auth


# Initialize MCP
mcp = FastApiMCP(
    app,
    include_operations=[
        "query", "register", "login",
        "read_users_me", "update_user_me",
        "delete_user_me", "read_users", "read_user",
    ],
    auth_config=AuthConfig(
        dependencies=[Depends(auth._get_current_user)],
    ),
)

mcp.mount()
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
