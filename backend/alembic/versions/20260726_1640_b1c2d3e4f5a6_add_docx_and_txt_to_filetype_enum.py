"""add_docx_and_txt_to_filetype_enum

Revision ID: b1c2d3e4f5a6
Revises: ef16e53f04f2
Create Date: 2026-07-26 16:40:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "ef16e53f04f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE filetype ADD VALUE IF NOT EXISTS 'docx';")
    op.execute("ALTER TYPE filetype ADD VALUE IF NOT EXISTS 'txt';")
    op.execute("ALTER TYPE chatrole ADD VALUE IF NOT EXISTS 'user';")
    op.execute("ALTER TYPE chatrole ADD VALUE IF NOT EXISTS 'assistant';")
    op.execute("ALTER TABLE document_contents ADD COLUMN IF NOT EXISTS content_metadata JSON;")
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'processingstage') THEN
            CREATE TYPE processingstage AS ENUM (
                'uploaded', 'extracting', 'chunking', 'embedding', 'indexing', 'completed', 'failed'
            );
        END IF;
    END $$;
    """)
    op.execute("""
    DO $$
    BEGIN
        ALTER TABLE processing_jobs ALTER COLUMN current_stage DROP DEFAULT;
        ALTER TABLE processing_jobs ALTER COLUMN current_stage TYPE processingstage USING current_stage::processingstage;
        ALTER TABLE processing_jobs ALTER COLUMN current_stage SET DEFAULT 'uploaded'::processingstage;
    EXCEPTION
        WHEN OTHERS THEN NULL;
    END $$;
    """)


def downgrade() -> None:
    pass
