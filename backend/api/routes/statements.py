from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from api.deps import get_current_user
from core.logger import get_logger
from db.session import get_db
from models.statement import ParsingStatus, StatementUpload
from models.user import User
from modules.ai_categorization.main import process_bank_statement
from modules.ai_categorization.parsing import ParsingError, PasswordRequiredError
from modules.ingestion.persistence import persist_parsed_transaction
from modules.ingestion.prompt_context import build_custom_rules_text, build_predefined_categories_text
from schemas.statement import StatementBatchResponse, StatementFileResult, StatementListItem

router = APIRouter(prefix="/statements", tags=["statements"])
logger = get_logger("api.statements")

AI_SERVICE_UNAVAILABLE_MESSAGE = (
    "Our document processing service is temporarily unavailable. Please try again in a few minutes."
)

EXTENSION_TO_SOURCE_TYPE = {
    ".csv": "csv",
    ".xls": "excel",
    ".xlsx": "excel",
    ".pdf": "pdf",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
}


def _source_type_for(filename: str) -> str:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return EXTENSION_TO_SOURCE_TYPE.get(ext, "pdf")


def _process_one_file(
    db: Session,
    statement: StatementUpload,
    file_bytes: bytes,
    filename: str,
    current_user: User,
    predefined_categories: str,
    custom_rules: str,
    password: str | None = None,
    raise_on_password_required: bool = False,
) -> StatementFileResult:
    """Runs the parse->sanitize->categorize->persist pipeline for one file against an
    already-created StatementUpload row, committing that row's own outcome regardless
    of what happens to any other file in the same batch.

    `raise_on_password_required` controls how a locked PDF is reported: the batch
    upload endpoint wants an in-band LOCKED result (so one file needing a password
    doesn't blow up the whole batch response), while the single-file retry endpoint
    wants a real `PasswordRequiredError` to propagate so it can return a true 423
    per .agents/AGENTS.md's documented contract.
    """
    try:
        transactions = process_bank_statement(
            file_bytes=file_bytes,
            filename=filename,
            custom_rules=custom_rules,
            predefined_categories=predefined_categories,
            password=password,
        )
        for parsed in transactions:
            persist_parsed_transaction(db, parsed, current_user, statement.statement_id)

        statement.parsing_status = ParsingStatus.COMPLETED
        db.commit()
        return StatementFileResult(
            statement_id=statement.statement_id,
            file_name=filename,
            status=statement.parsing_status.value,
            transactions_created=len(transactions),
        )
    except PasswordRequiredError:
        statement.parsing_status = ParsingStatus.LOCKED
        db.commit()
        if raise_on_password_required:
            raise
        return StatementFileResult(
            statement_id=statement.statement_id,
            file_name=filename,
            status=statement.parsing_status.value,
            requires_password=True,
        )
    except ParsingError as e:
        statement.parsing_status = ParsingStatus.FAILED
        db.commit()
        return StatementFileResult(
            statement_id=statement.statement_id,
            file_name=filename,
            status=statement.parsing_status.value,
            error=str(e),
        )
    except Exception:
        # Most likely an exhausted/failed Gemini call (categorization) that isn't a
        # ParsingError — never let the real exception (provider error text, status
        # codes) reach the client; the user just needs to know this file didn't go
        # through and can retry, not why in provider terms.
        logger.exception(f"Unexpected failure processing statement file '{filename}'")
        statement.parsing_status = ParsingStatus.FAILED
        db.commit()
        return StatementFileResult(
            statement_id=statement.statement_id,
            file_name=filename,
            status=statement.parsing_status.value,
            error=AI_SERVICE_UNAVAILABLE_MESSAGE,
        )


@router.post("", response_model=StatementBatchResponse, status_code=status.HTTP_201_CREATED)
def upload_statements(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Accepts multiple files in one request (any mix of CSV/Excel/PDF/JPG/PNG). Each
    file gets its own StatementUpload row and is processed independently — one file
    failing or needing a password never fails the rest of the batch.
    """
    predefined_categories = build_predefined_categories_text(db)
    custom_rules = build_custom_rules_text(db, current_user.user_id)

    results = []
    for upload in files:
        file_bytes = upload.file.read()
        statement = StatementUpload(
            user_id=current_user.user_id,
            file_name=upload.filename,
            upload_date=datetime.now(timezone.utc),
            parsing_status=ParsingStatus.PROCESSING,
            source_type=_source_type_for(upload.filename),
        )
        db.add(statement)
        db.flush()  # assigns statement.statement_id without ending the transaction

        results.append(_process_one_file(
            db, statement, file_bytes, upload.filename, current_user,
            predefined_categories, custom_rules,
        ))

    return StatementBatchResponse(results=results)


@router.get("", response_model=list[StatementListItem])
def list_statements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Powers the ingestion page's recent-uploads/processing-queue list."""
    return (
        db.query(StatementUpload)
        .filter(StatementUpload.user_id == current_user.user_id)
        .order_by(StatementUpload.upload_date.desc())
        .all()
    )


@router.post("/{statement_id}/retry", response_model=StatementFileResult)
def retry_locked_statement(
    statement_id: UUID,
    password: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retries a LOCKED (password-protected) statement. The client must re-send the
    same file alongside the password — raw file bytes are never persisted server-side
    (see .agents/AGENTS.md), so there is nothing stored here to retry against.
    """
    statement = (
        db.query(StatementUpload)
        .filter(StatementUpload.statement_id == statement_id, StatementUpload.user_id == current_user.user_id)
        .first()
    )
    if statement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Statement not found")
    if statement.parsing_status != ParsingStatus.LOCKED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This statement is not awaiting a password")

    predefined_categories = build_predefined_categories_text(db)
    custom_rules = build_custom_rules_text(db, current_user.user_id)
    file_bytes = file.file.read()

    try:
        return _process_one_file(
            db, statement, file_bytes, statement.file_name, current_user,
            predefined_categories, custom_rules, password=password,
            raise_on_password_required=True,
        )
    except PasswordRequiredError:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Incorrect password")
