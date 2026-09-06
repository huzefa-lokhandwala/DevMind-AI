"""Add users table and user ownership foreign keys to repositories and conversations

Revision ID: 005_user_auth_schema
Revises: 004_embedding_dim_768
Create Date: 2026-09-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '005_user_auth_schema'
down_revision: Union[str, None] = '004_embedding_dim_768'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. Add user_id to repositories
    op.add_column('repositories', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_repositories_user_id'), 'repositories', ['user_id'], unique=False)
    op.create_foreign_key(
        'fk_repositories_user_id_users',
        'repositories',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE',
    )

    # 3. Add user_id to conversations
    op.add_column('conversations', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_conversations_user_id'), 'conversations', ['user_id'], unique=False)
    op.create_foreign_key(
        'fk_conversations_user_id_users',
        'conversations',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    # 1. Drop user_id foreign key and column from conversations
    op.drop_constraint('fk_conversations_user_id_users', 'conversations', type_='foreignkey')
    op.drop_index(op.f('ix_conversations_user_id'), table_name='conversations')
    op.drop_column('conversations', 'user_id')

    # 2. Drop user_id foreign key and column from repositories
    op.drop_constraint('fk_repositories_user_id_users', 'repositories', type_='foreignkey')
    op.drop_index(op.f('ix_repositories_user_id'), table_name='repositories')
    op.drop_column('repositories', 'user_id')

    # 3. Drop users table
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
