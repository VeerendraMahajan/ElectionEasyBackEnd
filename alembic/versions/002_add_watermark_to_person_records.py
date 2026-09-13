"""add watermark to person_records

Revision ID: 002_watermark
Revises: 001_initial
Create Date: 2026-09-13 18:21:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_watermark'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('person_records', sa.Column('watermark', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('person_records', 'watermark')
