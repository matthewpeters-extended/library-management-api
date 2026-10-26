from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_role
from app.models import Author, Book, User
from app.schemas import AuthorCreate, AuthorOut, AuthorUpdate

router = APIRouter(prefix="/authors", tags=["authors"])


@router.get("", response_model=list[AuthorOut])
def list_authors(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Matches author name"),
    db: Session = Depends(get_db),
):
    query = db.query(Author)
    if search:
        query = query.filter(Author.name.ilike(f"%{search}%"))
    return query.offset(skip).limit(limit).all()


@router.get("/{author_id}", response_model=AuthorOut)
def get_author(author_id: int, db: Session = Depends(get_db)):
    author = db.get(Author, author_id)
    if author is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Author not found")
    return author


@router.post("", response_model=AuthorOut, status_code=status.HTTP_201_CREATED)
def create_author(
    payload: AuthorCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Admin", "Librarian")),
):
    author = Author(**payload.model_dump())
    db.add(author)
    db.commit()
    db.refresh(author)
    return author


@router.put("/{author_id}", response_model=AuthorOut)
def update_author(
    author_id: int,
    payload: AuthorUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Admin", "Librarian")),
):
    author = db.get(Author, author_id)
    if author is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Author not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(author, field, value)

    db.commit()
    db.refresh(author)
    return author


@router.delete("/{author_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_author(
    author_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Admin")),
):
    author = db.get(Author, author_id)
    if author is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Author not found")

    has_books = db.query(Book).filter(Book.author_id == author_id).first() is not None
    if has_books:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Cannot delete an author who has books"
        )

    db.delete(author)
    db.commit()
