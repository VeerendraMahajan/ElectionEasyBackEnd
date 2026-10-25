"""add booth details to person_records

Revision ID: 003_booth_details
Revises: 002_watermark
Create Date: 2026-10-22 10:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_booth_details'
down_revision: Union[str, None] = '002_watermark'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('person_records', sa.Column('booth_number', sa.String(length=50), nullable=True))
    op.add_column('person_records', sa.Column('booth_name_hi', sa.String(length=500), nullable=True))
    op.add_column('person_records', sa.Column('booth_name_en', sa.String(length=500), nullable=True))
    op.add_column('person_records', sa.Column('booth_address_hi', sa.Text(), nullable=True))
    op.add_column('person_records', sa.Column('booth_address_en', sa.Text(), nullable=True))
    op.create_index('ix_person_records_booth_number', 'person_records', ['booth_number'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_person_records_booth_number', table_name='person_records')
    op.drop_column('person_records', 'booth_address_en')
    op.drop_column('person_records', 'booth_address_hi')
    op.drop_column('person_records', 'booth_name_en')
    op.drop_column('person_records', 'booth_name_hi')
    op.drop_column('person_records', 'booth_number')
