"""Add admin field for user

Revision ID: eddd4abafc33
Revises: c76513259483
Create Date: 2021-10-04 14:16:22.537669

"""
from alembic import op
import sqlalchemy as sa
import ormar


# revision identifiers, used by Alembic.
revision = "eddd4abafc33"
down_revision = "c76513259483"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=True))
    op.execute("UPDATE users SET is_admin = false")
    op.alter_column("users", "is_admin", nullable=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("users", "is_admin")
    # ### end Alembic commands ###
