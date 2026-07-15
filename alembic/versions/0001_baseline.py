"""baseline — schema como estava antes das alocações de estoque (PEPS)

Revision ID: 0001_baseline
Revises:
Create Date: 2026-07-15

Este arquivo não altera nada. Ele existe só como um marco: como o projeto
usava `Base.metadata.create_all()` sem Alembic até agora, não dá pra gerar
automaticamente o histórico de tudo que já existe no banco. Rode:

    alembic stamp 0001_baseline

numa cópia do banco que já está rodando em produção/local, pra dizer ao
Alembic "considere que o banco já está neste ponto, não tente recriar nada".
Depois disso, `alembic upgrade head` aplica só a migração seguinte (0002),
que é a que de fato adiciona a tabela nova.

Se o banco for novo (ambiente de desenvolvimento vazio, ou primeira vez
rodando em produção), não precisa rodar `stamp` — só `alembic upgrade head`
já cria tudo do zero, incluindo o que esta migração representaria.
"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
