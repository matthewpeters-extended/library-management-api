from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_role
from app.models import BorrowRecord, User
from app.schemas import BorrowRecordOut

router = APIRouter(prefix="/borrow-records", tags=["borrow-records"])


@router.get("", response_model=list[BorrowRecordOut])
def list_borrow_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    active_only: bool = Query(False, description="Only records not yet returned"),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("Admin", "Librarian")),
):
    query = db.query(BorrowRecord)
    if active_only:
        query = query.filter(BorrowRecord.returned_at.is_(None))
    return query.offset(skip).limit(limit).all()
