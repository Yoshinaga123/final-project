import os
import pytest
from app import create_app
from apps.models import db, User

@pytest.fixture(scope='session')
def app():
    os.environ['FLASK_CONFIG'] = 'testing'
    application = create_app('testing')
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()

@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture(autouse=True)
def ensure_logged_out(app):
    """各テスト開始前にログイン状態をクリア"""
    from flask_login import logout_user
    with app.app_context():
        try:
            logout_user()
        except Exception:
            pass

@pytest.fixture()
def user(app):
    from apps.models import User
    u = User(username='tester', email='tester@example.com')
    u.set_password('secret123')
    db.session.add(u)
    db.session.commit()
    return u
