def test_list_authors_is_public(client, author):
    response = client.get("/authors")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_member_cannot_create_author(client, member_token, auth_header):
    response = client.post(
        "/authors", json={"name": "New Author"}, headers=auth_header(member_token)
    )
    assert response.status_code == 403


def test_admin_can_delete_author_without_books(client, admin_token, auth_header):
    headers = auth_header(admin_token)
    created = client.post("/authors", json={"name": "Deletable"}, headers=headers)
    author_id = created.json()["id"]

    response = client.delete(f"/authors/{author_id}", headers=headers)
    assert response.status_code == 204


def test_cannot_delete_author_with_books(client, admin_token, auth_header, author):
    headers = auth_header(admin_token)
    client.post("/books", json={"isbn": "has-author", "author_id": author.id}, headers=headers)

    response = client.delete(f"/authors/{author.id}", headers=headers)
    assert response.status_code == 400
