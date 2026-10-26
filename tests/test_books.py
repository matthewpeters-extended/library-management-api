def test_list_books_is_public(client):
    response = client.get("/books")
    assert response.status_code == 200
    assert response.json() == []


def test_member_cannot_create_book(client, member_token, auth_header, author):
    response = client.post(
        "/books",
        json={"isbn": "111", "author_id": author.id},
        headers=auth_header(member_token),
    )
    assert response.status_code == 403


def test_librarian_can_create_book(client, librarian_token, auth_header, author):
    response = client.post(
        "/books",
        json={"isbn": "111", "author_id": author.id},
        headers=auth_header(librarian_token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "Available"


def test_create_book_rejects_unknown_author(client, admin_token, auth_header):
    response = client.post(
        "/books", json={"isbn": "111", "author_id": 999}, headers=auth_header(admin_token)
    )
    assert response.status_code == 400


def test_create_book_rejects_duplicate_isbn(client, admin_token, auth_header, author):
    headers = auth_header(admin_token)
    first = client.post("/books", json={"isbn": "111", "author_id": author.id}, headers=headers)
    assert first.status_code == 201

    second = client.post("/books", json={"isbn": "111", "author_id": author.id}, headers=headers)
    assert second.status_code == 400


def test_get_book_not_found(client):
    response = client.get("/books/999")
    assert response.status_code == 404


def test_member_cannot_delete_book(client, admin_token, member_token, auth_header, author):
    created = client.post(
        "/books", json={"isbn": "111", "author_id": author.id}, headers=auth_header(admin_token)
    )
    book_id = created.json()["id"]

    response = client.delete(f"/books/{book_id}", headers=auth_header(member_token))
    assert response.status_code == 403


def test_admin_can_delete_book_with_no_history(client, admin_token, auth_header, author):
    headers = auth_header(admin_token)
    created = client.post("/books", json={"isbn": "111", "author_id": author.id}, headers=headers)
    book_id = created.json()["id"]

    response = client.delete(f"/books/{book_id}", headers=headers)
    assert response.status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_search_matches_isbn_or_author_name(client, admin_token, auth_header, author):
    headers = auth_header(admin_token)
    client.post("/books", json={"isbn": "unique-isbn-123", "author_id": author.id}, headers=headers)

    by_isbn = client.get("/books?search=unique-isbn")
    assert len(by_isbn.json()) == 1

    by_author = client.get(f"/books?search={author.name}")
    assert len(by_author.json()) == 1

    no_match = client.get("/books?search=nothing-matches-this")
    assert no_match.json() == []


def test_pagination_limits_results(client, admin_token, auth_header, author):
    headers = auth_header(admin_token)
    for i in range(5):
        client.post("/books", json={"isbn": f"isbn-{i}", "author_id": author.id}, headers=headers)

    page = client.get("/books?skip=0&limit=2")
    assert len(page.json()) == 2

    next_page = client.get("/books?skip=2&limit=2")
    assert len(next_page.json()) == 2
    assert page.json()[0]["id"] != next_page.json()[0]["id"]
