from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import BookStatus, UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


class BookCreate(BaseModel):
    isbn: str
    published_date: date | None = None
    author_id: int


class BookUpdate(BaseModel):
    isbn: str | None = None
    published_date: date | None = None
    author_id: int | None = None
    status: BookStatus | None = None


class BookOut(BaseModel):
    id: int
    isbn: str
    published_date: date | None
    author_id: int
    status: BookStatus

    model_config = ConfigDict(from_attributes=True)


class AuthorCreate(BaseModel):
    name: str
    bio: str | None = None
    birthdate: date | None = None


class AuthorUpdate(BaseModel):
    name: str | None = None
    bio: str | None = None
    birthdate: date | None = None


class AuthorOut(BaseModel):
    id: int
    name: str
    bio: str | None
    birthdate: date | None

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole


class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    role: UserRole | None = None


class BorrowRecordOut(BaseModel):
    id: int
    user_id: int
    book_id: int
    borrowed_at: datetime
    due_at: datetime
    returned_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
