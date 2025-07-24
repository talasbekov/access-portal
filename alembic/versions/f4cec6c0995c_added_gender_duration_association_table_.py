"""Added gender, duration, association table request_checkpoint

Revision ID: f4cec6c0995c
Revises: d54817f4b38e
Create Date: 2025-06-16 10:02:03.144150

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f4cec6c0995c"
down_revision: Union[str, None] = "d54817f4b38e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### create gender enum type ###
    gender_enum = sa.Enum("MALE", "FEMALE", name="genderenum")
    gender_enum.create(op.get_bind(), checkfirst=True)

    # ### add gender column with default and NOT NULL ###
    op.add_column(
        "request_persons",
        sa.Column(
            "gender", gender_enum, nullable=False, server_default=sa.text("'MALE'")
        ),
    )

    # ### create requestduration enum type ###
    duration_enum = sa.Enum("SHORT_TERM", "LONG_TERM", name="requestduration")
    duration_enum.create(op.get_bind(), checkfirst=True)

    # ### add duration column with default and NOT NULL ###
    op.add_column(
        "requests",
        sa.Column(
            "duration",
            duration_enum,
            nullable=False,
            server_default=sa.text("'SHORT_TERM'"),
        ),
    )

    # ### remove old one-to-many checkpoint relation ###
    op.drop_constraint(
        op.f("requests_checkpoint_id_fkey"), "requests", type_="foreignkey"
    )
    op.drop_column("requests", "checkpoint_id")

    # ### create association table for many-to-many ###
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("request_checkpoint"):
        op.create_table(
            "request_checkpoint",
            sa.Column(
                "request_id",
                sa.Integer(),
                sa.ForeignKey("requests.id"),
                primary_key=True,
            ),
            sa.Column(
                "checkpoint_id",
                sa.Integer(),
                sa.ForeignKey("checkpoints.id"),
                primary_key=True,
            ),
        )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### drop association table ###
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("request_checkpoint"):
        op.drop_table("request_checkpoint")

    # ### restore one-to-many checkpoint relation ###
    op.add_column(
        "requests",
        sa.Column("checkpoint_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        op.f("requests_checkpoint_id_fkey"),
        "requests",
        "checkpoints",
        ["checkpoint_id"],
        ["id"],
    )

    # ### drop duration column and enum type ###
    op.drop_column("requests", "duration")
    duration_enum = sa.Enum("SHORT_TERM", "LONG_TERM", name="requestduration")
    duration_enum.drop(op.get_bind(), checkfirst=True)

    # ### drop gender column and enum type ###
    op.drop_column("request_persons", "gender")
    gender_enum = sa.Enum("MALE", "FEMALE", name="genderenum")
    gender_enum.drop(op.get_bind(), checkfirst=True)
