"""adiciona stock_allocations e campos de rastreamento de custo em venda_items

Revision ID: 0002_stock_allocations
Revises: 0001_baseline
Create Date: 2026-07-15

Suporta venda sob encomenda sem inventar custo:
- cria a tabela stock_allocations (qual lote cobriu qual parte de qual item de venda)
- venda_items ganha quantity_allocated e cost_status (PENDENTE/PARCIAL/COMPLETO)
- venda_items.unit_cost e .profit passam a aceitar NULL (só ficam definitivos
  quando cost_status == "COMPLETO")
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_stock_allocations"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stock_allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("venda_item_id", sa.Integer(), nullable=False),
        sa.Column("stock_lot_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.Float(), nullable=False),
        sa.Column("date", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["venda_item_id"], ["venda_items.id"]),
        sa.ForeignKeyConstraint(["stock_lot_id"], ["stock_lots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_stock_allocations_venda_item_id", "stock_allocations", ["venda_item_id"]
    )
    op.create_index(
        "ix_stock_allocations_stock_lot_id", "stock_allocations", ["stock_lot_id"]
    )

    # batch_alter_table garante compatibilidade com SQLite, que não suporta
    # ALTER COLUMN direto (o modo batch recria a tabela por baixo dos panos).
    with op.batch_alter_table("venda_items") as batch_op:
        batch_op.add_column(
            sa.Column("quantity_allocated", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("cost_status", sa.String(), nullable=False, server_default="PENDENTE")
        )
        batch_op.alter_column("unit_cost", existing_type=sa.Float(), nullable=True)
        batch_op.alter_column("profit", existing_type=sa.Float(), nullable=True)

    # Dados que já existiam: o sistema antigo sempre "inventava" um custo
    # (fallback em cost_price) quando faltava estoque, então não dá pra saber
    # retroativamente de qual lote aquilo teria vindo de verdade. Tratamos
    # tudo que já tinha unit_cost preenchido como já coberto (COMPLETO), pra
    # não quebrar o histórico — só vendas NOVAS, feitas depois desta
    # migração, passam a ficar PENDENTE/PARCIAL de verdade quando faltar estoque.
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE venda_items
        SET cost_status = 'COMPLETO', quantity_allocated = quantity
        WHERE unit_cost IS NOT NULL
    """))


def downgrade() -> None:
    with op.batch_alter_table("venda_items") as batch_op:
        batch_op.alter_column("profit", existing_type=sa.Float(), nullable=False)
        batch_op.alter_column("unit_cost", existing_type=sa.Float(), nullable=False)
        batch_op.drop_column("cost_status")
        batch_op.drop_column("quantity_allocated")

    op.drop_index("ix_stock_allocations_stock_lot_id", table_name="stock_allocations")
    op.drop_index("ix_stock_allocations_venda_item_id", table_name="stock_allocations")
    op.drop_table("stock_allocations")
