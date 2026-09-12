"""Daily housekeeping: permanently purge data whose recovery/retention window has
passed. Runs in-process via APScheduler (see main.py's startup wiring) — a single
Render free-tier dyno doesn't need a separate worker/broker for a once-a-day job.

Two independent things get purged here, sharing this module only because they're on
the same schedule:
- Discarded (REJECTED) transactions older than DISCARD_RETENTION_DAYS — see
  api/routes/transactions.py's _apply_review_status for where discarded_at is set.
- Chat sessions (AIAdvisoryQuery rows) older than CHAT_RETENTION_DAYS — nothing else
  ever cleans these up; see api/routes/advisory.py.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from core.logger import get_logger
from db.session import SessionLocal
from models.advisory import AIAdvisoryQuery
from models.asset import Asset
from models.transaction import Transaction

logger = get_logger("core.scheduled_cleanup")

DISCARD_RETENTION_DAYS = 30
CHAT_RETENTION_DAYS = 30


def purge_discarded_transactions(db: Session) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=DISCARD_RETENTION_DAYS)
    stale = (
        db.query(Transaction)
        .filter(Transaction.review_status == "REJECTED", Transaction.discarded_at < cutoff)
        .all()
    )
    for transaction in stale:
        # Mirrors api/routes/transactions.py's _hard_delete_transaction — a capital-item
        # purchase has a linked Asset row that must go first or the FK rejects the delete.
        linked_asset = db.query(Asset).filter(Asset.transaction_id == transaction.transaction_id).first()
        if linked_asset is not None:
            db.delete(linked_asset)
        db.delete(transaction)
    return len(stale)


def purge_old_chat_sessions(db: Session) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=CHAT_RETENTION_DAYS)
    deleted = (
        db.query(AIAdvisoryQuery)
        .filter(AIAdvisoryQuery.timestamp < cutoff)
        .delete(synchronize_session=False)
    )
    return deleted


def run_daily_cleanup() -> None:
    db = SessionLocal()
    try:
        discarded_count = purge_discarded_transactions(db)
        chat_count = purge_old_chat_sessions(db)
        db.commit()
        logger.info(
            f"Scheduled cleanup: purged {discarded_count} discarded transaction(s) "
            f"past {DISCARD_RETENTION_DAYS} days and {chat_count} chat turn(s) past {CHAT_RETENTION_DAYS} days."
        )
    except Exception:
        db.rollback()
        logger.exception("Scheduled cleanup failed")
    finally:
        db.close()
