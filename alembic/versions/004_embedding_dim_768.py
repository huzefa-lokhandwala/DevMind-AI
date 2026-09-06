"""Update embedding dimension to 768 for Gemini Embedding 2 and add repository metadata

Revision ID: 004_embedding_dim_768
Revises: 003_embedding_dim_384
Create Date: 2026-09-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = '004_embedding_dim_768'
down_revision: Union[str, None] = '003_embedding_dim_384'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add repository-level embedding metadata columns
    op.add_column('repositories', sa.Column('embedding_provider', sa.String(length=50), nullable=True))
    op.add_column('repositories', sa.Column('embedding_model', sa.String(length=100), nullable=True))
    op.add_column('repositories', sa.Column('embedding_dimension', sa.Integer(), nullable=True))

    # 2. Safely invalidate incompatible existing 384d vectors before resizing pgvector column to 768d.
    # Chunk contents, line numbers, file records, and metadata are 100% preserved.
    op.execute("UPDATE chunks SET embedding = NULL;")

    # 3. Alter pgvector column to Vector(768)
    op.alter_column(
        'chunks',
        'embedding',
        type_=Vector(768),
        existing_type=Vector(384),
        nullable=True,
    )


def downgrade() -> None:
    # 1. Nullify incompatible 768d vectors as they cannot be mathematically converted to 384d.
    op.execute("UPDATE chunks SET embedding = NULL;")

    # 2. Alter column back to Vector(384)
    op.alter_column(
        'chunks',
        'embedding',
        type_=Vector(384),
        existing_type=Vector(768),
        nullable=True,
    )

    # 3. Drop repository metadata columns
    op.drop_column('repositories', 'embedding_dimension')
    op.drop_column('repositories', 'embedding_model')
    op.drop_column('repositories', 'embedding_provider')
