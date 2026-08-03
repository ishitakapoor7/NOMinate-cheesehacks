"""Add avatar_url to users

Revision ID: a1b2c3d4e5f6
Revises: 04c1428fc12a
Create Date: 2026-08-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '04c1428fc12a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('avatar_url', sa.String(length=1024), nullable=True))


def downgrade():
    op.drop_column('users', 'avatar_url')
