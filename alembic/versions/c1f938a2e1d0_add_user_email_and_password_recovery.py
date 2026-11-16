"""add_user_email_and_password_recovery

Revision ID: c1f938a2e1d0
Revises: af63832edcea
Create Date: 2026-11-15 23:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1f938a2e1d0'
down_revision: Union[str, Sequence[str], None] = 'af63832edcea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('debe_cambiar_password', sa.Boolean(), server_default=sa.text('0'), nullable=False))
        batch_op.add_column(sa.Column('reset_password_token', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('reset_password_expires', sa.DateTime(), nullable=True))
        batch_op.create_index(batch_op.f('ix_usuarios_email'), ['email'], unique=True)
        batch_op.create_index(batch_op.f('ix_usuarios_reset_password_token'), ['reset_password_token'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_usuarios_reset_password_token'))
        batch_op.drop_index(batch_op.f('ix_usuarios_email'))
        batch_op.drop_column('reset_password_expires')
        batch_op.drop_column('reset_password_token')
        batch_op.drop_column('debe_cambiar_password')
        batch_op.drop_column('email')
