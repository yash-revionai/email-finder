"""Initial schema for the Phase 1 backend foundation."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lookups",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("first_name", sa.String(length=255), nullable=False),
        sa.Column("last_name", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("verifier_calls_used", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="ck_lookups_confidence_range"),
        sa.CheckConstraint(
            "verifier_calls_used >= 0 AND verifier_calls_used <= 3",
            name="ck_lookups_verifier_calls_used_range",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lookups_domain"), "lookups", ["domain"], unique=False)
    op.create_index(op.f("ix_lookups_email"), "lookups", ["email"], unique=False)
    op.create_index(op.f("ix_lookups_first_name"), "lookups", ["first_name"], unique=False)
    op.create_index(op.f("ix_lookups_last_name"), "lookups", ["last_name"], unique=False)
    op.create_index(op.f("ix_lookups_status"), "lookups", ["status"], unique=False)

    op.create_table(
        "domain_patterns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("is_catch_all", sa.Boolean(), nullable=True),
        sa.Column(
            "patterns",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("last_successful_pattern", sa.String(length=128), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain"),
    )

    op.create_table(
        "verifier_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lookup_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("verifier", sa.String(length=64), nullable=False),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("credits_used", sa.Integer(), nullable=False),
        sa.Column(
            "called_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.CheckConstraint("credits_used >= 0", name="ck_verifier_calls_credits_used_non_negative"),
        sa.ForeignKeyConstraint(["lookup_id"], ["lookups.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_verifier_calls_email"), "verifier_calls", ["email"], unique=False)
    op.create_index(op.f("ix_verifier_calls_lookup_id"), "verifier_calls", ["lookup_id"], unique=False)
    op.create_index(op.f("ix_verifier_calls_result"), "verifier_calls", ["result"], unique=False)
    op.create_index(op.f("ix_verifier_calls_verifier"), "verifier_calls", ["verifier"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_verifier_calls_verifier"), table_name="verifier_calls")
    op.drop_index(op.f("ix_verifier_calls_result"), table_name="verifier_calls")
    op.drop_index(op.f("ix_verifier_calls_lookup_id"), table_name="verifier_calls")
    op.drop_index(op.f("ix_verifier_calls_email"), table_name="verifier_calls")
    op.drop_table("verifier_calls")

    op.drop_table("domain_patterns")

    op.drop_index(op.f("ix_lookups_status"), table_name="lookups")
    op.drop_index(op.f("ix_lookups_last_name"), table_name="lookups")
    op.drop_index(op.f("ix_lookups_first_name"), table_name="lookups")
    op.drop_index(op.f("ix_lookups_email"), table_name="lookups")
    op.drop_index(op.f("ix_lookups_domain"), table_name="lookups")
    op.drop_table("lookups")
