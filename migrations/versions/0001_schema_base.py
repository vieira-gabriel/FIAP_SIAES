"""schema base

Ponto de partida vazio: cria só o controle de versões do Alembic. As tabelas entram com cada
entidade, nas Fases 4 e 5.

Revision ID: 0001
Revises:
Create Date: 2026-10-24 12:00:00

"""

from collections.abc import Sequence

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
