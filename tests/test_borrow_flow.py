import pytest


@pytest.fixture()
def available_book(client, admin_token, auth_header, author):
    response = client.post(
        "/books", json={"isbn": "borrow-me", "author_id": author.id}, headers=auth_header(admin_token)
    )
    return response.json()


def test_member_can_borrow_available_book(client, member_token, auth_header, available_book):
    response = client.post(
        f"/books/{available_book['id']}/borrow", headers=auth_header(member_token)
    )
    assert response.status_code == 200
    record = response.json()
    assert record["returned_at"] is None

    book = client.get(f"/books/{available_book['id']}").json()
    assert book["status"] == "Borrowed"


def test_cannot_borrow_already_borrowed_book(client, member_token, auth_header, available_book):
    headers = auth_header(member_token)
    client.post(f"/books/{available_book['id']}/borrow", headers=headers)

    second_attempt = client.post(f"/books/{available_book['id']}/borrow", headers=headers)
    assert second_attempt.status_code == 400


def test_librarian_cannot_borrow(client, librarian_token, auth_header, available_book):
    response = client.post(
        f"/books/{available_book['id']}/borrow", headers=auth_header(librarian_token)
    )
    assert response.status_code == 403


def test_member_can_return_borrowed_book(client, member_token, auth_header, available_book):
    headers = auth_header(member_token)
    client.post(f"/books/{available_book['id']}/borrow", headers=headers)

    response = client.post(f"/books/{available_book['id']}/return", headers=headers)
    assert response.status_code == 200
    assert response.json()["returned_at"] is not None

    book = client.get(f"/books/{available_book['id']}").json()
    assert book["status"] == "Available"


def test_returning_without_active_borrow_fails(client, member_token, auth_header, available_book):
    response = client.post(
        f"/books/{available_book['id']}/return", headers=auth_header(member_token)
    )
    assert response.status_code == 400


def test_cannot_delete_book_with_borrow_history(
    client, admin_token, member_token, auth_header, available_book
):
    client.post(f"/books/{available_book['id']}/borrow", headers=auth_header(member_token))
    client.post(f"/books/{available_book['id']}/return", headers=auth_header(member_token))

    response = client.delete(f"/books/{available_book['id']}", headers=auth_header(admin_token))
    assert response.status_code == 400


def test_borrow_records_visible_to_admin_only(
    client, admin_token, librarian_token, member_token, auth_header, available_book
):
    client.post(f"/books/{available_book['id']}/borrow", headers=auth_header(member_token))

    forbidden = client.get("/borrow-records", headers=auth_header(member_token))
    assert forbidden.status_code == 403

    admin_view = client.get("/borrow-records", headers=auth_header(admin_token))
    assert admin_view.status_code == 200
    assert len(admin_view.json()) == 1

    librarian_view = client.get("/borrow-records", headers=auth_header(librarian_token))
    assert librarian_view.status_code == 200
