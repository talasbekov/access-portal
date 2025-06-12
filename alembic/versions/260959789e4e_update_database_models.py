"""update_database_models

Revision ID: 260959789e4e
Revises: 3da7417286b3
Create Date: 2025-06-12 07:09:29.865295

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '260959789e4e'
down_revision: Union[str, None] = '3da7417286b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
