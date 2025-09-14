from apps import create_app
from apps.models import db, User


def login(client, username, password):
    return client.post('/auth/login', data={'username': username, 'password': password}, follow_redirects=True)


def create_user(app):
    with app.app_context():
        u = User(username='detector_user', email='detector@example.com')
        u.set_password('secret123')
        db.session.add(u)
        db.session.commit()
        return u


def test_detector_health_ok(client, app):
    # 事前にユーザー作成とログイン
    u = create_user(app)
    resp = login(client, 'detector_user', 'secret123')
    assert resp.status_code == 200

    # /detector/health が 200 か 503 を返すこと（起動時の依存状況で変動）
    resp2 = client.get('/detector/health')
    assert resp2.status_code in (200, 503)
    data = resp2.get_json()
    assert 'ok' in data
    assert 'components' in data


def test_detector_debug_requires_login(client):
    # ログインなしでヘルスへアクセス -> 認証リダイレクト
    resp = client.get('/detector/health', follow_redirects=False)
    assert resp.status_code in (301, 302, 303, 307)
    assert '/auth/login' in resp.headers.get('Location', '')
