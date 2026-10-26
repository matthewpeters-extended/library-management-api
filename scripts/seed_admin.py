"""One-off: create the first Admin user so you can log in and create the rest via the API."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine
from app.models import User, UserRole
from app.security import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()

existing = db.query(User).filter(User.email == "admin@mylibrary.dev").first()
if existing:
    print("Admin already exists.")
else:
    admin = User(
        name="Admin",
        email="admin@mylibrary.dev",
        password=hash_password("admin123"),
        role=UserRole.admin,
    )
    db.add(admin)
    db.commit()
    print("Created admin@mylibrary.dev / admin123")

db.close()
