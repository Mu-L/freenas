"""Mail OAuth provider

Revision ID: bda3a0ff206e
Revises: bb352e66987f
Create Date: 2024-12-02 13:45:00.262906+00:00

"""
import json

from alembic import op
import sqlalchemy as sa

from middlewared.plugins.pwenc import encrypt, decrypt


# revision identifiers, used by Alembic.
revision = 'bda3a0ff206e'
down_revision = 'bb352e66987f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    conn = op.get_bind()
    for id, em_oauth in conn.execute("SELECT id, em_oauth FROM system_email").fetchall():
        if em_oauth := decrypt(em_oauth):
            em_oauth = json.loads(em_oauth)
            if em_oauth:
                em_oauth["provider"] = "gmail"
                conn.execute(
                    "UPDATE system_email SET em_oauth = ? WHERE id = ?",
                    (encrypt(json.dumps(em_oauth)), id)
                )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
