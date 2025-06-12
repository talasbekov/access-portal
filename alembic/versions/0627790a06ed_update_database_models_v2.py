"""update_database_models_v2

Revision ID: 0627790a06ed
Revises: 260959789e4e
Create Date: 2025-06-12 07:10:39.353645

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0627790a06ed'
down_revision: Union[str, None] = '260959789e4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
