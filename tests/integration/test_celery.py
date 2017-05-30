import pytest

@pytest.mark.priority(10)
def test_session(session, api_url):
    r = session.get(api_url('user/me'))
    assert r.status_code == 200
    assert r.json()['login'] == 'admin'
    assert r.json()['admin'] == True
    assert r.json()['status'] == 'enabled'
