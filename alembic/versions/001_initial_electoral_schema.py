"""Initial electoral schema

Revision ID: 001_initial
Revises: 
Create Date: 2026-09-13 13:38:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('total_pages', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sha256')
    )
    op.create_index('ix_documents_sha256', 'documents', ['sha256'], unique=True)
    op.create_index('ix_documents_status', 'documents', ['status'], unique=False)

    # 2. extraction_jobs table
    op.create_table(
        'extraction_jobs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('total_documents', sa.Integer(), nullable=False),
        sa.Column('processed_documents', sa.Integer(), nullable=False),
        sa.Column('total_pages', sa.Integer(), nullable=False),
        sa.Column('processed_pages', sa.Integer(), nullable=False),
        sa.Column('total_records', sa.Integer(), nullable=False),
        sa.Column('processed_records', sa.Integer(), nullable=False),
        sa.Column('failed_records', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_extraction_jobs_status', 'extraction_jobs', ['status'], unique=False)

    # 3. document_pages table
    op.create_table(
        'document_pages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('assembly_number', sa.String(length=50), nullable=True),
        sa.Column('assembly_name_hi', sa.String(length=255), nullable=True),
        sa.Column('assembly_name_en', sa.String(length=255), nullable=True),
        sa.Column('section_number', sa.String(length=50), nullable=True),
        sa.Column('section_name_hi', sa.String(length=500), nullable=True),
        sa.Column('section_name_en', sa.String(length=500), nullable=True),
        sa.Column('part_number', sa.String(length=50), nullable=True),
        sa.Column('booth_number', sa.String(length=50), nullable=True),
        sa.Column('booth_name_hi', sa.String(length=500), nullable=True),
        sa.Column('booth_name_en', sa.String(length=500), nullable=True),
        sa.Column('booth_address_hi', sa.Text(), nullable=True),
        sa.Column('booth_address_en', sa.Text(), nullable=True),
        sa.Column('page_width', sa.Float(), nullable=True),
        sa.Column('page_height', sa.Float(), nullable=True),
        sa.Column('raw_header_text', sa.Text(), nullable=True),
        sa.Column('header_bbox', sa.JSON(), nullable=True),
        sa.Column('header_confidence', sa.Float(), nullable=True),
        sa.Column('extraction_method', sa.String(length=100), nullable=True),
        sa.Column('processing_status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_document_pages_document_id', 'document_pages', ['document_id'], unique=False)
    op.create_index('ix_document_pages_page_number', 'document_pages', ['page_number'], unique=False)
    op.create_index('ix_document_pages_assembly_number', 'document_pages', ['assembly_number'], unique=False)
    op.create_index('ix_document_pages_section_number', 'document_pages', ['section_number'], unique=False)
    op.create_index('ix_document_pages_part_number', 'document_pages', ['part_number'], unique=False)
    op.create_index('ix_document_pages_booth_number', 'document_pages', ['booth_number'], unique=False)
    op.create_index('ix_doc_page_unique', 'document_pages', ['document_id', 'page_number'], unique=True)
    op.create_index('ix_doc_page_hierarchy', 'document_pages', ['assembly_number', 'part_number', 'section_number', 'booth_number'])

    # 4. person_records table
    op.create_table(
        'person_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('page_id', sa.UUID(), nullable=False),
        sa.Column('serial_number', sa.Integer(), nullable=True),
        sa.Column('house_number', sa.String(length=100), nullable=True),
        sa.Column('name_hi', sa.String(length=255), nullable=True),
        sa.Column('name_en', sa.String(length=255), nullable=True),
        sa.Column('relation_type', sa.String(length=50), nullable=True),
        sa.Column('relation_name_hi', sa.String(length=255), nullable=True),
        sa.Column('relation_name_en', sa.String(length=255), nullable=True),
        sa.Column('id_number', sa.String(length=100), nullable=True),
        sa.Column('gender_hi', sa.String(length=20), nullable=True),
        sa.Column('gender_en', sa.String(length=20), nullable=True),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('photo_available', sa.Boolean(), nullable=True),
        sa.Column('raw_record_text', sa.Text(), nullable=True),
        sa.Column('source_bbox', sa.JSON(), nullable=True),
        sa.Column('overall_confidence', sa.Float(), nullable=False),
        sa.Column('validation_status', sa.String(length=50), nullable=False),
        sa.Column('correction_history', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['page_id'], ['document_pages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_person_records_document_id', 'person_records', ['document_id'], unique=False)
    op.create_index('ix_person_records_page_id', 'person_records', ['page_id'], unique=False)
    op.create_index('ix_person_records_id_number', 'person_records', ['id_number'], unique=False)
    op.create_index('ix_person_records_serial_number', 'person_records', ['serial_number'], unique=False)
    op.create_index('ix_person_records_validation_status', 'person_records', ['validation_status'], unique=False)
    op.create_index('ix_person_doc_page_serial', 'person_records', ['document_id', 'page_id', 'serial_number'])
    op.create_index('ix_person_validation_conf', 'person_records', ['validation_status', 'overall_confidence'])

    # 5. extraction_field_results table
    op.create_table(
        'extraction_field_results',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('person_record_id', sa.UUID(), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('raw_value', sa.Text(), nullable=True),
        sa.Column('normalized_value_hi', sa.Text(), nullable=True),
        sa.Column('normalized_value_en', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source_bbox', sa.JSON(), nullable=True),
        sa.Column('validation_status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['person_record_id'], ['person_records.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_extraction_field_results_person_record_id', 'extraction_field_results', ['person_record_id'], unique=False)
    op.create_index('ix_extraction_field_results_field_name', 'extraction_field_results', ['field_name'], unique=False)
    op.create_index('ix_field_record_name', 'extraction_field_results', ['person_record_id', 'field_name'])

    # 6. processing_errors table
    op.create_table(
        'processing_errors',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('page_id', sa.UUID(), nullable=True),
        sa.Column('record_id', sa.UUID(), nullable=True),
        sa.Column('error_type', sa.String(length=100), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('stack_trace', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['page_id'], ['document_pages.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_processing_errors_document_id', 'processing_errors', ['document_id'], unique=False)
    op.create_index('ix_processing_errors_page_id', 'processing_errors', ['page_id'], unique=False)
    op.create_index('ix_processing_errors_error_type', 'processing_errors', ['error_type'], unique=False)
    op.create_index('ix_error_doc_page', 'processing_errors', ['document_id', 'page_id'])


def downgrade() -> None:
    op.drop_table('processing_errors')
    op.drop_table('extraction_field_results')
    op.drop_table('person_records')
    op.drop_table('document_pages')
    op.drop_table('extraction_jobs')
    op.drop_table('documents')
