"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2025-03-04 00:28:23.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create blocks table
    op.create_table(
        'blocks',
        sa.Column('hash', sa.String(64), primary_key=True),
        sa.Column('previous_hash', sa.String(64)),
        sa.Column('timestamp', sa.Float),
        sa.Column('nonce', sa.Integer),
        sa.Column('difficulty', sa.Integer),
        sa.Column('merkle_root', sa.String(64)),
        sa.Column('height', sa.Integer, unique=True),
    )

    # Create transactions table
    op.create_table(
        'transactions',
        sa.Column('hash', sa.String(64), primary_key=True),
        sa.Column('sender', sa.String(40)),
        sa.Column('recipient', sa.String(40)),
        sa.Column('amount', sa.Float),
        sa.Column('timestamp', sa.Float),
        sa.Column('signature', sa.Text),
        sa.Column('nonce', sa.Integer),
        sa.Column('block_hash', sa.String(64), sa.ForeignKey('blocks.hash')),
        sa.Column('type', sa.String(20)),
        sa.Column('payload', sa.JSON),
    )

    # Create validators table
    op.create_table(
        'validators',
        sa.Column('address', sa.String(40), primary_key=True),
        sa.Column('stake_amount', sa.Float),
        sa.Column('last_validation', sa.Float),
        sa.Column('reputation', sa.Float),
        sa.Column('is_active', sa.Boolean),
    )

    # Create indices
    op.create_index('ix_blocks_height', 'blocks', ['height'])
    op.create_index('ix_transactions_sender', 'transactions', ['sender'])
    op.create_index('ix_transactions_recipient', 'transactions', ['recipient'])
    op.create_index('ix_transactions_block_hash', 'transactions', ['block_hash'])

def downgrade():
    op.drop_table('transactions')
    op.drop_table('validators')
    op.drop_table('blocks')
