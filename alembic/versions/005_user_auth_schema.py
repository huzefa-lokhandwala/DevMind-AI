"""Add users table, conversations, messages, and user ownership foreign keys

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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # 1. Create users table if not exists
    if 'users' not in tables:
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
    if 'repositories' in tables:
        repo_cols = {col['name'] for col in inspector.get_columns('repositories')}
        if 'user_id' not in repo_cols:
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

    # 3. Create or update conversations table
    if 'conversations' not in tables:
        op.create_table(
            'conversations',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('session_id', sa.String(length=128), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('repository_name', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_conversations_session_id'), 'conversations', ['session_id'], unique=False)
        op.create_index(op.f('ix_conversations_user_id'), 'conversations', ['user_id'], unique=False)
    else:
        conv_cols = {col['name'] for col in inspector.get_columns('conversations')}
        if 'user_id' not in conv_cols:
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

    # 4. Create messages table if not exists
    if 'messages' not in tables:
        op.create_table(
            'messages',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('conversation_id', sa.String(length=36), nullable=False),
            sa.Column('role', sa.String(length=20), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('intent', sa.String(length=50), nullable=True),
            sa.Column('sources_json', sa.Text(), nullable=True),
            sa.Column('provider', sa.String(length=100), nullable=True),
            sa.Column('model', sa.String(length=100), nullable=True),
            sa.Column('latency_ms', sa.Float(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_messages_conversation_id'), 'messages', ['conversation_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'messages' in tables:
        op.drop_index(op.f('ix_messages_conversation_id'), table_name='messages')
        op.drop_table('messages')

    if 'conversations' in tables:
        conv_cols = {col['name'] for col in inspector.get_columns('conversations')}
        if 'user_id' in conv_cols:
            try:
                op.drop_constraint('fk_conversations_user_id_users', 'conversations', type_='foreignkey')
            except Exception:
                pass
            op.drop_index(op.f('ix_conversations_user_id'), table_name='conversations')
            op.drop_column('conversations', 'user_id')

    if 'repositories' in tables:
        repo_cols = {col['name'] for col in inspector.get_columns('repositories')}
        if 'user_id' in repo_cols:
            try:
                op.drop_constraint('fk_repositories_user_id_users', 'repositories', type_='foreignkey')
            except Exception:
                pass
            op.drop_index(op.f('ix_repositories_user_id'), table_name='repositories')
            op.drop_column('repositories', 'user_id')

    if 'users' in tables:
        op.drop_index(op.f('ix_users_email'), table_name='users')
        op.drop_table('users')
