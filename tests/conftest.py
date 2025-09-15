import os
import pytest

# Some CI jobs (e.g. Windows E2E bridge test) don't need the Flask app.
# Allow opting out via env or when the app module isn't importable.
USE_FLASK_FIXTURES = os.getenv("PYTEST_USE_FLASK", "1") == "1"
if USE_FLASK_FIXTURES:
    try:
        from app import create_app  # type: ignore
        from apps.models import db, User  # type: ignore
    except Exception:
        USE_FLASK_FIXTURES = False

if USE_FLASK_FIXTURES:
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
else:
    # When Flask fixtures are disabled, we define nothing.
    # Tests that require the Flask app should set PYTEST_USE_FLASK=1.
    pass
