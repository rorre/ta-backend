"""Add additional fields to course

Revision ID: a9e1956cba63
Revises: c53f55e9231e
Create Date: 2021-09-25 16:32:26.994697

"""
from alembic import op
import sqlalchemy as sa
import ormar


# revision identifiers, used by Alembic.
revision = 'a9e1956cba63'
down_revision = 'c53f55e9231e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('courses', sa.Column('datetime', sa.DateTime(timezone=True), nullable=False))
    op.add_column('courses', sa.Column('link', sa.Text(), nullable=True))
    op.add_column('courses', sa.Column('students_limit', sa.Integer(), nullable=True))
    op.add_column('courses', sa.Column('notes', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('courses', 'notes')
    op.drop_column('courses', 'students_limit')
    op.drop_column('courses', 'link')
    op.drop_column('courses', 'datetime')
    # ### end Alembic commands ###
