def test_member_cannot_list_users(client, member_token, auth_header):
    response = client.get("/users", headers=auth_header(member_token))
    assert response.status_code == 403


def test_admin_can_list_users(client, admin_token, auth_header):
    response = client.get("/users", headers=auth_header(admin_token))
    assert response.status_code == 200


def test_admin_can_create_user(client, admin_token, auth_header):
    response = client.post(
        "/users",
        json={
            "name": "New Librarian",
            "email": "new-librarian@test-suite.dev",
            "password": "secret123",
            "role": "Librarian",
        },
        headers=auth_header(admin_token),
    )
    assert response.status_code == 201
    assert "password" not in response.json()


def test_cannot_create_user_with_duplicate_email(client, admin_token, auth_header, member_user):
    response = client.post(
        "/users",
        json={
            "name": "Dup",
            "email": "member@test-suite.dev",
            "password": "secret123",
            "role": "Member",
        },
        headers=auth_header(admin_token),
    )
    assert response.status_code == 400


def test_cannot_delete_user_with_borrow_history(
    client, admin_token, member_token, auth_header, author
):
    headers = auth_header(admin_token)
    book = client.post("/books", json={"isbn": "u-hist", "author_id": author.id}, headers=headers).json()
    client.post(f"/books/{book['id']}/borrow", headers=auth_header(member_token))

    me = client.get("/me", headers=auth_header(member_token)).json()
    response = client.delete(f"/users/{me['id']}", headers=headers)
    assert response.status_code == 400
