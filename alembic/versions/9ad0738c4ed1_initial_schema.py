"""initial schema

Revision ID: 9ad0738c4ed1
Revises:
Create Date: 2026-07-08 13:32:13.621657

This migration establishes the baseline schema. It is written to be safe
to run against two very different starting points without any manual steps:

  1. A brand new, empty database (new deployment) -> creates every table
     from scratch, identical to what `Base.metadata.create_all()` used to
     do on app startup.
  2. An existing production database that has been running the app before
     Alembic existed (schema created by the old `create_all()` +
     `ensure_schema_compat()` combo) -> every step below is a no-op, since
     the tables/columns already exist. No data is touched.

`Base.metadata.create_all(checkfirst=True)` is used instead of hand-written
`op.create_table()` calls specifically here, in the *first* migration, so
the baseline is guaranteed to match the live model definitions exactly (no
risk of hand-transcription drift). Every migration after this one should be
generated the normal Alembic way (`alembic revision --autogenerate`), which
diffs the real database against the current models -- it does not replay
this file, so this shortcut does not affect future migrations.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.db.database import Base
from app import models  # noqa: F401  (registers all tables on Base.metadata)

# revision identifiers, used by Alembic.
revision: str = '9ad0738c4ed1'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Mirrors the old ensure_schema_compat() statements from app/main.py /
# scripts/bootstrap.py, for any pre-Alembic database old enough to be
# missing them. All-new installs already get these via create_all above;
# any database that has booted the app in the last several releases already
# has them applied. Kept only as a defensive no-op safety net.
_LEGACY_COMPAT_STATEMENTS = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_pending_approval BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE billing_periods ADD COLUMN IF NOT EXISTS closed_at TIMESTAMP",
    "ALTER TABLE drinks ADD COLUMN IF NOT EXISTS stock_quantity INTEGER",
    "ALTER TABLE drinks ADD COLUMN IF NOT EXISTS low_stock_threshold INTEGER NOT NULL DEFAULT 5",
    "ALTER TABLE consumptions DROP COLUMN IF EXISTS team_id",
    "ALTER TABLE consumptions DROP COLUMN IF EXISTS fridge_id",
    "ALTER TABLE drinks DROP COLUMN IF EXISTS team_id",
    "ALTER TABLE drinks DROP COLUMN IF EXISTS fridge_id",
    "ALTER TABLE users DROP COLUMN IF EXISTS team_id",
    "DROP TABLE IF EXISTS fridges CASCADE",
    "DROP TABLE IF EXISTS teams CASCADE",
]


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # Only touches tables/columns that don't already exist -- safe on a
    # database that already has this exact schema.
    Base.metadata.create_all(bind=bind, checkfirst=True)

    inspector = sa.inspect(bind)
    if inspector.has_table("users") and inspector.has_table("drinks") and inspector.has_table("consumptions"):
        for statement in _LEGACY_COMPAT_STATEMENTS:
            op.execute(sa.text(statement))


def downgrade() -> None:
    """Downgrade schema.

    Drops every table managed by this app. This is destructive by design
    (it is the mirror image of the create_all above) -- do not run this
    against a database you care about.
    """
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind, checkfirst=True)
