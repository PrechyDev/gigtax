import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from db.base_class import Base


class Asset(Base):
    """A capital item (laptop, camera, equipment, vehicle) whose cost is written off
    over several years via a First Schedule capital allowance, not deducted in full in
    its purchase year. See modules/tax_computation/capital_allowances.py for the
    per-class annual rate and modules/tax_computation/loader.py for how this feeds
    into the tax engine.
    """
    __tablename__ = "assets"

    asset_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    # The originating purchase transaction, if this asset was derived from one
    # (ingestion or manual entry) rather than declared standalone. Nullable so a user
    # can also register an asset they already owned before using this system.
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.transaction_id"), nullable=True)

    # Matches Transaction.description's length (500) since this is usually copied
    # straight from the originating transaction — see modules/ingestion/asset_sync.py.
    description = Column(String(500), nullable=False)
    cost = Column(Float, nullable=False)
    purchase_date = Column(DateTime(timezone=True), nullable=False)
    asset_class = Column(String(20), nullable=False)  # "class_1" | "class_2" | "class_3"

    disposed = Column(Boolean, default=False)
    disposed_date = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="assets")
    transaction = relationship("Transaction")
