from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_role
from app.models import Author, Book, BookStatus, BorrowRecord, User
from app.schemas import BookCreate, BookOut, BookUpdate, BorrowRecordOut

router = APIRouter(prefix="/books", tags=["books"])

BORROW_PERIOD_DAYS = 14


@router.get("", response_model=list[BookOut])
def list_books(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Matches ISBN or author name"),
    db: Session = Depends(get_db),
):
    query = db.query(Book)
    if search:
        query = query.join(Author).filter(
            (Book.isbn.ilike(f"%{search}%")) | (Author.name.ilike(f"%{search}%"))
        )
    return query.offset(skip).limit(limit).all()


@router.get("/{book_id}", response_model=BookOut)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Book not found")
    return book


@router.post("", response_model=BookOut, status_code=status.HTTP_201_CREATED)
def create_book(
    payload: BookCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Admin", "Librarian")),
):
    author = db.get(Author, payload.author_id)
    if author is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "author_id does not exist")

    book = Book(**payload.model_dump(), status=BookStatus.available)
    db.add(book)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "isbn already exists")
    db.refresh(book)
    return book


@router.put("/{book_id}", response_model=BookOut)
def update_book(
    book_id: int,
    payload: BookUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Admin", "Librarian")),
):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Book not found")

    data = payload.model_dump(exclude_unset=True)

    if "author_id" in data and db.get(Author, data["author_id"]) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "author_id does not exist")

    for field, value in data.items():
        setattr(book, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "isbn already exists")
    db.refresh(book)
    return book


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Admin")),
):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Book not found")

    has_borrow_history = (
        db.query(BorrowRecord).filter(BorrowRecord.book_id == book_id).first()
        is not None
    )
    if has_borrow_history:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot delete a book with borrow history (active or past)",
        )

    db.delete(book)
    db.commit()


@router.post("/{book_id}/borrow", response_model=BorrowRecordOut)
def borrow_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Member")),
):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Book not found")
    if book.status != BookStatus.available:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Book is not available")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    record = BorrowRecord(
        user_id=current_user.id,
        book_id=book.id,
        borrowed_at=now,
        due_at=now + timedelta(days=BORROW_PERIOD_DAYS),
    )
    book.status = BookStatus.borrowed

    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.post("/{book_id}/return", response_model=BorrowRecordOut)
def return_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Member")),
):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Book not found")

    record = (
        db.query(BorrowRecord)
        .filter(
            BorrowRecord.book_id == book_id,
            BorrowRecord.user_id == current_user.id,
            BorrowRecord.returned_at.is_(None),
        )
        .first()
    )
    if record is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "You have no active borrow on this book"
        )

    record.returned_at = datetime.now(timezone.utc).replace(tzinfo=None)
    book.status = BookStatus.available

    db.commit()
    db.refresh(record)
    return record
