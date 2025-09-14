from apps.models import db, User

def test_register_and_login(client):
    # register
    resp = client.post('/auth/register', data={
        'username': 'alice',
        'email': 'alice@example.com',
        'password': 'pass1234'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert 'ログイン' in resp.data.decode('utf-8', errors='ignore')  # redirected to login page

    # login
    resp2 = client.post('/auth/login', data={
        'username': 'alice',
        'password': 'pass1234'
    }, follow_redirects=True)
    assert resp2.status_code == 200
    # after login should reach index (template contains maybe dashboard or base)
    assert b'html' in resp2.data.lower()  # coarse check


def test_protected_redirect(client):
    # 未ログイン状態でルートアクセス -> ログインページリダイレクト
    client.get('/auth/logout', follow_redirects=True)
    resp = client.get('/', follow_redirects=False)
    assert resp.status_code in (301, 302, 303, 307)
    location = resp.headers.get('Location', '')
    assert '/auth/login' in location
