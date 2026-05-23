"""tandem_insulin

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-23 23:37:07.607404

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "basal_events",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("rate_units_per_hour", sa.Numeric(6, 3), nullable=False),
        sa.Column("delivery_type", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False, server_default="tandem_source"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(
        "idx_basal_recorded_at", "basal_events", ["recorded_at"], unique=False
    )

    op.create_table(
        "bolus_events",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("insulin_units", sa.Numeric(6, 3), nullable=False),
        sa.Column("requested_units", sa.Numeric(6, 3), nullable=True),
        sa.Column("carbs_grams", sa.Numeric(6, 1), nullable=True),
        sa.Column("bg_input_mgdl", sa.SmallInteger(), nullable=True),
        sa.Column("bolus_type", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False, server_default="tandem_source"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(
        "idx_bolus_recorded_at", "bolus_events", ["recorded_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("idx_bolus_recorded_at", table_name="bolus_events")
    op.drop_table("bolus_events")
    op.drop_index("idx_basal_recorded_at", table_name="basal_events")
    op.drop_table("basal_events")
