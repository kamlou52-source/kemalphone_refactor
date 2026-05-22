
import os
import tempfile
import pytest

@pytest.fixture(scope="session")
def test_db_path(tmp_path_factory):
    dbfile = tmp_path_factory.mktemp("db") / "test.db"
    return str(dbfile)

@pytest.fixture(scope="session")
def app(test_db_path, monkeypatch):
    # Force app to use a temp sqlite file BEFORE importing
    monkeypatch.setenv("KEMAL_DB", test_db_path)
    from app import app as flask_app, db
    with flask_app.app_context():
        db.drop_all()
        db.create_all()
    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    yield flask_app

@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture()
def db(app):
    from app import db as _db
    with app.app_context():
        yield _db
