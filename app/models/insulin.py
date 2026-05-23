from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, SmallInteger, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BasalEvent(Base):
    __tablename__ = "basal_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    rate_units_per_hour: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    delivery_type: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="tandem_source")


class BolusEvent(Base):
    __tablename__ = "bolus_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    insulin_units: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    requested_units: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    carbs_grams: Mapped[Decimal | None] = mapped_column(Numeric(6, 1))
    bg_input_mgdl: Mapped[int | None] = mapped_column(SmallInteger)
    bolus_type: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="tandem_source")
