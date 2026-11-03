"""Add browser-bound, encrypted PKCE login attempts without changing existing data."""

from alembic import op
import sqlalchemy as sa
from app.models import UTCDateTime

revision = "0002_google_login"
down_revision = "0001_concierge"
branch_labels = None
depends_on = None


def upgrade():
    if not sa.inspect(op.get_bind()).has_table("oauth_login_attempts"):
        op.create_table(
            "oauth_login_attempts",
            sa.Column("token_hash", sa.String(64), primary_key=True),
            sa.Column("verifier_ciphertext", sa.Text(), nullable=False),
            sa.Column("expires_at", UTCDateTime(timezone=True), nullable=False),
            sa.Column("used_at", UTCDateTime(timezone=True), nullable=True),
        )
        op.create_index(
            "ix_oauth_login_attempts_expires_at", "oauth_login_attempts", ["expires_at"]
        )


def downgrade():
    raise RuntimeError("Retain the additive schema when rolling back application code")
