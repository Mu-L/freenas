"""Remove system.general language column.

Revision ID: cf1f98f4c3b1
Revises: a34e4c124c25
Create Date: 2025-03-14 19:25:23.879521+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cf1f98f4c3b1'
down_revision = 'a34e4c124c25'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('system_settings', schema=None) as batch_op:
        batch_op.drop_column('stg_language')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('system_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('stg_language', sa.VARCHAR(length=120), nullable=False))

    # ### end Alembic commands ###
