from datetime import date as date_type
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db
from ..stock_utils import recalculate_average_cost
from .vendas import _aplicar_alocacoes

router = APIRouter(
    prefix="/entradas",
    tags=["Entradas"],
    dependencies=[Depends(security.get_current_user)],
)


def _to_out(db: Session, entrada: models.Entrada) -> schemas.EntradaOut:
    lot = db.query(models.StockLot).filter(models.StockLot.entrada_id == entrada.id).first()
    pode_editar = lot is not None and lot.quantity_remaining == lot.quantity_received
    return schemas.EntradaOut(
        id=entrada.id, date=entrada.date, product_id=entrada.product_id,
        product_name=entrada.product_name, quantity=entrada.quantity,
        unit_cost=entrada.unit_cost, total_cost=entrada.total_cost,
        pode_editar=pode_editar,
    )


def _reconciliar_pendentes(db: Session, product: models.Product, lot: models.StockLot) -> None:
    """Quando um lote novo chega, primeiro quita o custo de vendas desse
    produto que ficaram pendentes/parciais (venda sob encomenda) — a mais
    antiga primeiro, mesmo critério de justiça do PEPS — antes de deixar o
    saldo do lote livre para vendas futuras."""
    pendentes = (
        db.query(models.VendaItem)
        .join(models.Venda)
        .filter(
            models.VendaItem.product_id == product.id,
            models.VendaItem.cost_status != "COMPLETO",
        )
        .order_by(models.Venda.date.asc(), models.Venda.id.asc(), models.VendaItem.id.asc())
        .all()
    )

    for item in pendentes:
        if lot.quantity_remaining <= 0:
            break

        faltante = item.quantity - item.quantity_allocated
        if faltante <= 0:
            continue

        consumida = min(faltante, lot.quantity_remaining)
        if consumida <= 0:
            continue

        _aplicar_alocacoes(db, item, [(lot, consumida)], date_type.today().isoformat())
        db.flush()


@router.get("", response_model=List[schemas.EntradaOut])
def list_entradas(db: Session = Depends(get_db)):
    entradas = db.query(models.Entrada).order_by(models.Entrada.id.desc()).all()
    return [_to_out(db, e) for e in entradas]


@router.post("", response_model=schemas.EntradaOut, status_code=status.HTTP_201_CREATED)
def registrar_entrada(payload: schemas.EntradaCreate, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == payload.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    total_cost = round(payload.quantity * payload.unit_cost, 2)

    entrada = models.Entrada(
        date=payload.date, product_id=product.id, product_name=product.name,
        quantity=payload.quantity, unit_cost=payload.unit_cost, total_cost=total_cost,
    )
    db.add(entrada)
    db.flush()

    lot = models.StockLot(
        product_id=product.id, entrada_id=entrada.id, date=payload.date,
        quantity_received=payload.quantity, quantity_remaining=payload.quantity,
        unit_cost=payload.unit_cost,
    )
    db.add(lot)
    db.flush()

    # Antes de contar esse estoque como "livre", quita vendas sob encomenda
    # antigas desse produto que ainda estavam sem custo confirmado.
    _reconciliar_pendentes(db, product, lot)

    product.stock += payload.quantity
    db.flush()
    recalculate_average_cost(product, db)

    db.commit()
    db.refresh(entrada)
    return _to_out(db, entrada)


@router.put("/{entrada_id}", response_model=schemas.EntradaOut)
def editar_entrada(entrada_id: int, payload: schemas.EntradaUpdate, db: Session = Depends(get_db)):
    entrada = db.query(models.Entrada).filter(models.Entrada.id == entrada_id).first()
    if not entrada:
        raise HTTPException(status_code=404, detail="Entrada não encontrada.")

    lot = db.query(models.StockLot).filter(models.StockLot.entrada_id == entrada.id).first()
    if not lot or lot.quantity_remaining != lot.quantity_received:
        raise HTTPException(
            status_code=409,
            detail="Essa entrada já teve produto vendido/alocado e não pode mais ser editada. "
                   "Registre uma nova entrada para corrigir a diferença.",
        )

    product = db.query(models.Product).filter(models.Product.id == entrada.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    product.stock -= entrada.quantity

    entrada.date = payload.date
    entrada.quantity = payload.quantity
    entrada.unit_cost = payload.unit_cost
    entrada.total_cost = round(payload.quantity * payload.unit_cost, 2)

    lot.date = payload.date
    lot.quantity_received = payload.quantity
    lot.quantity_remaining = payload.quantity
    lot.unit_cost = payload.unit_cost

    product.stock += payload.quantity

    db.flush()

    # A entrada corrigida também pode agora cobrir vendas pendentes.
    _reconciliar_pendentes(db, product, lot)

    recalculate_average_cost(product, db)

    db.commit()
    db.refresh(entrada)
    return _to_out(db, entrada)


@router.delete("/{entrada_id}", status_code=status.HTTP_204_NO_CONTENT)
def apagar_entrada(entrada_id: int, db: Session = Depends(get_db)):
    entrada = db.query(models.Entrada).filter(models.Entrada.id == entrada_id).first()
    if not entrada:
        raise HTTPException(status_code=404, detail="Entrada não encontrada.")

    lot = db.query(models.StockLot).filter(models.StockLot.entrada_id == entrada.id).first()
    if not lot or lot.quantity_remaining != lot.quantity_received:
        raise HTTPException(
            status_code=409,
            detail="Essa entrada já teve produto vendido/alocado e não pode mais ser apagada. "
                   "Registre uma nova entrada para corrigir a diferença.",
        )

    product = db.query(models.Product).filter(models.Product.id == entrada.product_id).first()
    if product:
        product.stock -= entrada.quantity

    db.delete(lot)
    db.delete(entrada)

    if product:
        db.flush()
        recalculate_average_cost(product, db)

    db.commit()
