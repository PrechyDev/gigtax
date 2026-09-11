from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from api.deps import get_current_user
from core.logger import get_logger
from db.session import get_db
from models.tax import TaxComputation, TaxReport
from models.user import User
from modules.reporting.generator import build_report_pdf
from modules.tax_computation.engine import compute_tax
from modules.tax_computation.loader import (
    load_capital_allowance_items,
    load_capital_allowances_for_year,
    load_categorized_transactions,
)
from modules.tax_computation.reporting_helpers import build_itemized_breakdown
from services.drive_service import DriveService

router = APIRouter(prefix="/tax-computations", tags=["reports"])
logger = get_logger("api.reports")


def _record_report_in_drive(db: Session, user: User, tax_year: str, file_id: str) -> None:
    computation = (
        db.query(TaxComputation)
        .filter(TaxComputation.user_id == user.user_id, TaxComputation.tax_year == tax_year)
        .first()
    )
    if computation is None:
        return  # nothing to attach the report record to yet — the PDF was still served

    existing_report = (
        db.query(TaxReport).filter(TaxReport.computation_id == computation.computation_id).first()
    )
    if existing_report:
        existing_report.storage_path = file_id
    else:
        db.add(TaxReport(computation_id=computation.computation_id, storage_path=file_id, format="PDF"))
    db.commit()


@router.get("/{tax_year}/report")
def download_report(
    tax_year: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generates the self-assessment PDF on demand from current approved transactions
    (not from a possibly-stale stored TaxComputation) and streams it straight back. If
    Google Drive is connected, also drops a copy there as a convenience log — but a
    failure in that optional step must never cost the user their PDF.
    """
    transactions = load_categorized_transactions(db, current_user, tax_year)
    capital_allowances = load_capital_allowances_for_year(db, current_user.user_id, tax_year)
    capital_allowance_items = load_capital_allowance_items(db, current_user.user_id, tax_year)
    result = compute_tax(transactions, capital_allowances_this_year=capital_allowances)
    items = build_itemized_breakdown(db, transactions, capital_allowance_items)
    pdf_bytes = build_report_pdf(current_user.name, tax_year, result, items)

    if current_user.google_drive_connected:
        try:
            file_id = DriveService(current_user).upload(
                file_bytes=pdf_bytes,
                filename=f"GigTax-Report-{tax_year}.pdf",
                mime_type="application/pdf",
                folder_id=current_user.google_drive_folder_id,
            )
            _record_report_in_drive(db, current_user, tax_year, file_id)
        except Exception:
            logger.exception("Failed to back up generated report to Google Drive (non-fatal)")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="GigTax-Report-{tax_year}.pdf"'},
    )
