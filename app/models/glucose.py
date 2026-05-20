from datetime import datetime

from sqlalchemy import BigInteger, DateTime, SmallInteger, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GlucoseReading(Base):
    __tablename__ = "glucose_readings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    reading_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    glucose_mgdl: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    trend: Mapped[str] = mapped_column(Text, nullable=False)
    trend_arrow: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="dexcom_share")
