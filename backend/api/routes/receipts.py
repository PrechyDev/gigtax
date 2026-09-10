from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from api.deps import get_current_user
from core.logger import get_logger
from db.session import get_db
from models.receipt import Receipt
from models.transaction import Transaction
from models.user import User
from schemas.receipt import ReceiptOut
from services.drive_service import DriveService

router = APIRouter(prefix="/transactions/{transaction_id}/receipts", tags=["receipts"])
logger = get_logger("api.receipts")

DRIVE_UNAVAILABLE_MESSAGE = "Couldn't reach Google Drive right now. Please try again shortly."


def _get_owned_transaction(db: Session, transaction_id: UUID, current_user: User) -> Transaction:
    transaction = (
        db.query(Transaction)
        .filter(Transaction.transaction_id == transaction_id, Transaction.user_id == current_user.user_id)
        .first()
    )
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return transaction


@router.post("", response_model=ReceiptOut, status_code=status.HTTP_201_CREATED)
def upload_receipt(
    transaction_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transaction = _get_owned_transaction(db, transaction_id, current_user)

    if not current_user.google_drive_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Connect Google Drive before uploading receipts (BYOS storage).",
        )

    file_bytes = file.file.read()
    try:
        drive_service = DriveService(current_user)
        file_id = drive_service.upload(
            file_bytes=file_bytes,
            filename=file.filename,
            mime_type=file.content_type or "application/octet-stream",
            folder_id=current_user.google_drive_folder_id,
        )
    except Exception:
        logger.exception(f"Drive upload failed for transaction {transaction_id}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=DRIVE_UNAVAILABLE_MESSAGE)

    receipt = Receipt(
        transaction_id=transaction.transaction_id,
        storage_path=file_id,
        file_type=file.content_type,
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return receipt


@router.get("", response_model=list[ReceiptOut])
def list_receipts(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_transaction(db, transaction_id, current_user)
    return db.query(Receipt).filter(Receipt.transaction_id == transaction_id).all()
