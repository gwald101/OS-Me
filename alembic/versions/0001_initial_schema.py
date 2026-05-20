"""initial_schema

Revision ID: 0001
Revises: 
Create Date: 2026-05-20 15:01:20.027398

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "glucose_readings",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("reading_id", sa.Text(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("glucose_mgdl", sa.SmallInteger(), nullable=False),
        sa.Column("trend", sa.Text(), nullable=False),
        sa.Column("trend_arrow", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False, server_default="dexcom_share"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reading_id"),
    )
    op.create_index(
        "idx_glucose_recorded_at", "glucose_readings", ["recorded_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("idx_glucose_recorded_at", table_name="glucose_readings")
    op.drop_table("glucose_readings")
