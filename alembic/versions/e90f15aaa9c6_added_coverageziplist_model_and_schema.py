"""Added CoverageZipList Model and Schema

Revision ID: e90f15aaa9c6
Revises: c6dead2155e8
Create Date: 2025-03-23 11:44:15.383368

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e90f15aaa9c6'
down_revision: Union[str, None] = 'c6dead2155e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
