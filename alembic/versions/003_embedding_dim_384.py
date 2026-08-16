"""Update embedding dimension to 384 for local FastEmbed BGE embeddings

Revision ID: 003_embedding_dim_384
Revises: 002_embedding_dim_768
Create Date: 2026-08-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = '003_embedding_dim_384'
down_revision: Union[str, None] = '002_embedding_dim_768'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullify incompatible 768d vectors before resizing pgvector column to 384d.
    # Chunk contents, line numbers, file records, and metadata are 100% preserved.
    op.execute("UPDATE chunks SET embedding = NULL;")
    op.alter_column(
        'chunks',
        'embedding',
        type_=Vector(384),
        existing_type=Vector(768),
        nullable=True,
    )


def downgrade() -> None:
    # Downgrading requires nullifying 384d vectors as they cannot be mathematically converted to 768d.
    op.execute("UPDATE chunks SET embedding = NULL;")
    op.alter_column(
        'chunks',
        'embedding',
        type_=Vector(768),
        existing_type=Vector(384),
        nullable=True,
    )
