def test_login_success(client, member_user):
    response = client.post(
        "/login", json={"email": "member@test-suite.dev", "password": "member123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password(client, member_user):
    response = client.post(
        "/login", json={"email": "member@test-suite.dev", "password": "wrong"}
    )
    assert response.status_code == 401


def test_login_unknown_email(client):
    response = client.post(
        "/login", json={"email": "nobody@test-suite.dev", "password": "whatever"}
    )
    assert response.status_code == 401


def test_me_requires_token(client):
    response = client.get("/me")
    assert response.status_code == 401


def test_me_returns_current_user(client, member_token, auth_header):
    response = client.get("/me", headers=auth_header(member_token))
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "member@test-suite.dev"
    assert body["role"] == "Member"
