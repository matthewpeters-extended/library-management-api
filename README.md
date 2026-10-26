# Library Management API

A REST API for a library: books, authors, users, and the borrow/return lifecycle between
them.

Stack: **FastAPI** + **SQLAlchemy** + **SQLite**, JWT auth via `python-jose`, password hashing
via `passlib`/`bcrypt`, rate limiting via `slowapi`.

## Quickstart

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/seed_admin.py        # creates admin@mylibrary.dev / admin123
python scripts/seed_test_data.py    # creates a sample author + a member user

uvicorn app.main:app --reload --reload-dir app
```

Interactive docs (Swagger UI) at `http://127.0.0.1:8000/docs` once it is running.

Run the test suite with:

```bash
pytest
```

## The main components

The app is split by *what each piece knows about*, not by HTTP verb. The goal is that each
file has one job and does not need to understand how the others work internally.

**`app/models.py` is the data layer.** Four SQLAlchemy tables mirroring the spec exactly:
`Author`, `Book`, `User`, `BorrowRecord`. `Book.status` and `User.role` are enums
(`Available`/`Borrowed`, `Admin`/`Librarian`/`Member`) rather than free text strings, so an
invalid status cannot make it into the database. `BorrowRecord` is the join point. It has its
own `id`, not just a composite key, because a user can borrow the same book more than once
over time (borrow, return, borrow again), and each of those needs to be a distinct row with
its own `borrowed_at`/`due_at`/`returned_at`.

**`app/database.py` is the connection.** One SQLAlchemy `engine` pointed at `library.db`, and a
`get_db()` generator that FastAPI's dependency system calls per request to hand out a session
and guarantee it is closed afterwards, even if the request raises an exception.

**`app/security.py` is crypto, with no web framework in it.** Two unrelated jobs live here on
purpose: hashing and verifying passwords (`passlib` + `bcrypt`), and encoding and decoding JWTs
(`python-jose`). Neither function knows what FastAPI, a route, or an HTTP request is, which is
what makes this file trivial to unit test and to reuse if the web layer ever changed.

**`app/deps.py` is the authorization gate every protected route passes through.**
`get_current_user` pulls the JWT off the `Authorization` header, decodes it, and loads the
matching `User` row, raising `401` at any point that fails. `require_role(*roles)` wraps that:
it is a dependency *factory*, so a route writes `Depends(require_role("Admin", "Librarian"))`
and gets both "is this person logged in" and "do they have the right role" checked before the
route body ever runs. This is the single place RBAC is enforced. No route reimplements the
logic; it just declares which roles it accepts.

**`app/routers/` holds the actual HTTP endpoints, one file per resource:**

<table>
<tr><th>File</th><th>Routes</th><th>Who can call what</th></tr>
<tr><td><code>auth.py</code></td><td><code>POST /login</code></td><td>Anyone with correct credentials; rate limited to 5 per minute</td></tr>
<tr><td><code>books.py</code></td><td><code>GET /books</code>, <code>GET /books/{id}</code>, <code>POST /books</code>, <code>PUT /books/{id}</code>, <code>DELETE /books/{id}</code>, <code>POST /books/{id}/borrow</code>, <code>POST /books/{id}/return</code></td><td>Reads are public; writes are Admin/Librarian; delete is Admin; borrow and return is Member</td></tr>
<tr><td><code>authors.py</code></td><td>Same CRUD shape as books, no borrow concept</td><td>Reads public, writes Admin/Librarian, delete Admin</td></tr>
<tr><td><code>users.py</code></td><td><code>GET /users</code>, <code>GET /users/{id}</code>, <code>POST /users</code>, <code>PUT /users/{id}</code>, <code>DELETE /users/{id}</code></td><td>Admin only, for everything; there is no self registration</td></tr>
<tr><td><code>borrow_records.py</code></td><td><code>GET /borrow-records</code></td><td>Admin/Librarian, to audit who has borrowed what</td></tr>
</table>

**`app/limiter.py` plus the `slowapi` wiring in `main.py` handle abuse prevention.** A
`Limiter` keyed by client IP, with a global default (100 requests per minute) and a stricter
limit specifically on `/login` (5 per minute) since that is the endpoint someone would actually
try to brute force.

**`app/main.py` assembles all of it.** Creates the tables on startup, registers the rate
limiter, and mounts each router. Nothing business specific lives here; it is purely wiring.

**`scripts/`** holds one time bootstrap scripts, not part of the running app. Since user
creation is Admin only, there is a chicken and egg problem: nothing can create the first Admin
through the API. `seed_admin.py` solves that directly against the database. `seed_test_data.py`
adds a sample author and a Member account for manual testing.

**`tests/`** has 31 pytest feature tests exercising the RBAC rules, the borrow/return state
machine, and the validation edge cases, against an in memory SQLite database so they never
touch `library.db`. The rate limiter is disabled in this environment only, since the test
client's requests all appear to come from the same IP and would otherwise trip the login limit
for reasons unrelated to what is actually being tested.

## Decisions worth knowing about

* **Deleting a `Book` or `Author` or `User` with existing `BorrowRecord` history is blocked
  (`400`), not silently cascaded.** The alternative, SQLAlchemy's default behavior, tries to
  null out `BorrowRecord.book_id`/`user_id`, which fails anyway since those columns are
  `NOT NULL`, and previously surfaced as an unhandled `500`. But even if it did not fail,
  cascading the delete would destroy the one thing a library most needs to keep: the record of
  who borrowed what, and when.
* **The JWT signing secret is hardcoded** in `security.py` (`"dev-secret-change-me"`). That is
  fine here since this is a practice project; in anything real it would come from an
  environment variable and never be committed.
* **Returning a book only works for the member who borrowed it.** The endpoint looks up an
  *active* `BorrowRecord` matching both `book_id` and the caller's own `user_id`, so one member
  cannot return a book someone else is holding.
