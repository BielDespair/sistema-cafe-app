"""baseline — cria o schema como ele estava antes das alocações de estoque (PEPS)

Revision ID: 0001_baseline
Revises:
Create Date: 2026-07-15

Duas formas de usar esta migração, dependendo do banco:

1) BANCO NOVO/VAZIO (ex: ambiente de teste local, ou primeiro deploy):
       alembic upgrade head
   Isso roda o `upgrade()` abaixo de verdade, criando as 8 tabelas originais,
   e depois a migração 0002 adiciona a parte de alocação PEPS por cima.

2) BANCO JÁ EXISTENTE com essas tabelas (criadas antes via
   `Base.metadata.create_all()`, sem Alembic — o caso de produção no Render
   antes desta atualização):
       alembic stamp 0001_baseline
       alembic upgrade head
   O `stamp` marca a versão SEM rodar o `upgrade()` (não tenta recriar nada
   que já existe), e o `upgrade head` seguinte aplica só a 0002.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_id", "users", ["id"])

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("sku", sa.String(), nullable=False),
        sa.Column("cost_price", sa.Float(), nullable=False),
        sa.Column("sell_price", sa.Float(), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_products_sku", "products", ["sku"], unique=True)
    op.create_index("ix_products_id", "products", ["id"])

    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("document", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("pix", sa.String(), nullable=True),
        sa.Column("zip_code", sa.String(), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("number", sa.String(), nullable=True),
        sa.Column("neighborhood", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clients_id", "clients", ["id"])

    op.create_table(
        "entradas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.String(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.Float(), nullable=False),
        sa.Column("total_cost", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_entradas_id", "entradas", ["id"])

    op.create_table(
        "stock_lots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("entrada_id", sa.Integer(), nullable=True),
        sa.Column("date", sa.String(), nullable=False),
        sa.Column("quantity_received", sa.Integer(), nullable=False),
        sa.Column("quantity_remaining", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["entrada_id"], ["entradas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stock_lots_id", "stock_lots", ["id"])

    op.create_table(
        "debts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.String(), nullable=False),
        sa.Column("product_name", sa.String(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("total_price", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_debts_id", "debts", ["id"])

    op.create_table(
        "vendas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.String(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("client_name", sa.String(), nullable=False),
        sa.Column("total_value", sa.Float(), nullable=False),
        sa.Column("is_paid", sa.Boolean(), nullable=False),
        sa.Column("payment_method", sa.String(), nullable=True),
        sa.Column("delivery_status", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vendas_id", "vendas", ["id"])

    op.create_table(
        "venda_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("venda_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("total_price", sa.Float(), nullable=False),
        sa.Column("unit_cost", sa.Float(), nullable=False),
        sa.Column("profit", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["venda_id"], ["vendas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_venda_items_id", "venda_items", ["id"])


def downgrade() -> None:
    op.drop_table("venda_items")
    op.drop_table("vendas")
    op.drop_table("debts")
    op.drop_table("stock_lots")
    op.drop_table("entradas")
    op.drop_table("clients")
    op.drop_table("products")
    op.drop_table("users")