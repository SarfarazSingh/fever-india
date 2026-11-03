"""Durable Gmail imports and at-most-once email submission tracking."""
from alembic import op
import sqlalchemy as sa
from app.models import UTCDateTime
revision = "0003_gmail_delivery"
down_revision = "0002_google_login"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    columns = {c["name"] for c in sa.inspect(bind).get_columns("mail_connections")}
    if "verifier_ciphertext" not in columns:
        op.add_column("mail_connections", sa.Column("verifier_ciphertext", sa.Text(), nullable=True))
    if "sync_state" not in columns:
        op.add_column("mail_connections", sa.Column("sync_state", sa.JSON(), nullable=False, server_default="{}"))
    if not sa.inspect(bind).has_table("email_deliveries"):
        op.create_table("email_deliveries",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("account_id", sa.String(80), sa.ForeignKey("accounts.id"), nullable=False),
            sa.Column("trip_id", sa.String(36), sa.ForeignKey("trips.id"), nullable=True),
            sa.Column("kind", sa.String(24), nullable=False),
            sa.Column("state", sa.String(24), nullable=False),
            sa.Column("message_id", sa.String(255), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("created_at", UTCDateTime(timezone=True), nullable=False),
            sa.Column("updated_at", UTCDateTime(timezone=True), nullable=False))
        op.create_index("ix_email_deliveries_account_id", "email_deliveries", ["account_id"])
        op.create_index("ix_email_deliveries_state", "email_deliveries", ["state"])

def downgrade():
    raise RuntimeError("Retain the additive schema when rolling back application code")
