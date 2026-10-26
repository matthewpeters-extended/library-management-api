from fastapi import FastAPI, Depends
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.database import Base, engine
from app import models  # noqa: F401  (import so Base knows about the tables)
from app.deps import get_current_user
from app.limiter import limiter
from app.models import User
from app.schemas import UserOut
from app.routers import auth, authors, books, borrow_records, users

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Library Management API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(auth.router)
app.include_router(books.router)
app.include_router(authors.router)
app.include_router(users.router)
app.include_router(borrow_records.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
