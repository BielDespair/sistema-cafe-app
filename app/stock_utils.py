from sqlalchemy.orm import Session

from . import models


def recalculate_average_cost(product: models.Product, db: Session) -> None:
    """Recalcula o custo médio do produto a partir dos lotes com saldo.

    Chamado sempre que um lote é criado, editado, apagado ou consumido numa
    venda — assim o custo de referência do produto nunca fica desatualizado,
    seja lá o que tenha mudado nos lotes.
    """
    lots = (
        db.query(models.StockLot)
        .filter(models.StockLot.product_id == product.id, models.StockLot.quantity_remaining > 0)
        .all()
    )
    total_qty = sum(lot.quantity_remaining for lot in lots)
    if total_qty > 0:
        total_value = sum(lot.quantity_remaining * lot.unit_cost for lot in lots)
        product.cost_price = total_value / total_qty
    # se não sobrou nenhum lote com saldo, mantém o último custo conhecido