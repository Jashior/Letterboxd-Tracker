"""Add display_order to Film model

Revision ID: 596dc0cc3660
Revises: e813ce16b099
Create Date: 2025-06-22 02:07:45.138440

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '596dc0cc3660'
down_revision = 'e813ce16b099'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('film', schema=None) as batch_op:
        batch_op.add_column(sa.Column('display_order', sa.Integer(), server_default='0', nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('film', schema=None) as batch_op:
        batch_op.drop_column('display_order')

    # ### end Alembic commands ###
