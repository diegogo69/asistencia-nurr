"""remove_qr_support

Revision ID: af63832edcea
Revises: 3d870ea360c4
Create Date: 2026-11-09 22:58:55.701632

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af63832edcea'
down_revision: Union[str, Sequence[str], None] = '3d870ea360c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - remove QR code column and index from usuarios."""
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_usuarios_codigo_qr'))
        batch_op.drop_column('codigo_qr')


def downgrade() -> None:
    """Downgrade schema - restore QR code column and index to usuarios."""
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.add_column(sa.Column('codigo_qr', sa.String(length=255), nullable=True))
        batch_op.create_index(batch_op.f('ix_usuarios_codigo_qr'), ['codigo_qr'], unique=True)
