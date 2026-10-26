"""One-off: seed a sample author + a member user, for manually exercising the API."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine
from app.models import Author, User, UserRole
from app.security import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()

author = db.query(Author).filter(Author.name == "George Orwell").first()
if author is None:
    author = Author(name="George Orwell", bio="English novelist and essayist.")
    db.add(author)
    db.commit()
    db.refresh(author)
    print(f"Created author id={author.id}: George Orwell")
else:
    print(f"Author already exists: id={author.id}")

member = db.query(User).filter(User.email == "member@mylibrary.dev").first()
if member is None:
    member = User(
        name="Test Member",
        email="member@mylibrary.dev",
        password=hash_password("member123"),
        role=UserRole.member,
    )
    db.add(member)
    db.commit()
    print("Created member@mylibrary.dev / member123")
else:
    print("Member already exists.")

db.close()
