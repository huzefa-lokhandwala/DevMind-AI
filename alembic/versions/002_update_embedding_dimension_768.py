"""Update embedding dimension to 768 for Gemini embeddings

Revision ID: 002_embedding_dim_768
Revises: 001_initial_schema
Create Date: 2026-08-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = '002_embedding_dim_768'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clear incompatible 384d vectors before resizing column to 768d
    op.execute("UPDATE chunks SET embedding = NULL;")
    op.alter_column(
        'chunks',
        'embedding',
        type_=Vector(768),
        existing_type=Vector(384),
        nullable=True,
    )


def downgrade() -> None:
    op.execute("UPDATE chunks SET embedding = NULL;")
    op.alter_column(
        'chunks',
        'embedding',
        type_=Vector(384),
        existing_type=Vector(768),
        nullable=True,
    )
