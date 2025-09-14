from apps.models import User

def test_password_hashing(user):
    assert user.check_password('secret123') is True
    assert user.check_password('wrong') is False
