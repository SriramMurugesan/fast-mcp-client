import os
import importlib
import sys

import pytest


@pytest.fixture(scope="function")
def auth_db():
    """Provide the db_backend_sqlalchemy module wired to an in-memory SQLite DB.

    We set POSTGRES_URL to an in-memory SQLite URL **before** importing the module
    so that its global engine points to the lightweight test DB. This keeps the
    unit-tests fast and self-contained while exercising the same ORM code.
    """
    os.environ["POSTGRES_URL"] = "sqlite:///:memory:"

    if "db_backend_sqlalchemy" in sys.modules:
        del sys.modules["db_backend_sqlalchemy"]

    import pathlib
    
    sys.path.append(str(pathlib.Path(__file__).parent.parent))
    import db_backend_sqlalchemy as db_backend

    db_backend.Base.metadata.create_all(bind=db_backend.engine)

    yield db_backend

    db_backend.Base.metadata.drop_all(bind=db_backend.engine)
