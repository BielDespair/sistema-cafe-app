from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas, security
from ..database import get_db
from ..stock_utils import recalculate_average_cost

router = APIRouter(
    prefix="/vendas",
    tags=["Vendas"],
    dependencies=[Depends(security.get_current_user)],
)


@router.get("", response_model=List[schemas.VendaOut])
def list_vendas(
    start: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="YYYY-MM-DD"),
    client_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(models.Venda).options(joinedload(models.Venda.items))

    if start:
        query = query.filter(models.Venda.date >= start)
    if end:
        query = query.filter(models.Venda.date <= end)
    if client_id:
        query = query.filter(models.Venda.client_id == client_id)

    return query.order_by(models.Venda.date.desc(), models.Venda.id.desc()).all()
def _consume_fifo(db: Session, product: models.Product, quantity: int) -> float:
    remaining = quantity
    total_cost = 0.0

    lots = (
        db.query(models.StockLot)
        .filter(models.StockLot.product_id == product.id, models.StockLot.quantity_remaining > 0)
        .order_by(models.StockLot.date.asc(), models.StockLot.id.asc())
        .all()
    )

    for lot in lots:
        if remaining <= 0:
            break
        consumed = min(lot.quantity_remaining, remaining)
        lot.quantity_remaining -= consumed
        total_cost += consumed * lot.unit_cost
        remaining -= consumed

    if remaining > 0:
        total_cost += remaining * product.cost_price

    return total_cost





@router.post("", response_model=schemas.VendaOut, status_code=status.HTTP_201_CREATED)
def registrar_venda(payload: schemas.VendaCreate, db: Session = Depends(get_db)):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Adicione pelo menos um produto.")
    if not payload.is_paid and not payload.client_id:
        raise HTTPException(status_code=400, detail="Para marcar como fiado, informe o cliente.")
    if payload.delivery_status == "PENDENTE" and not payload.client_id:
        raise HTTPException(status_code=400, detail="Para agendar entrega futura, informe o cliente.")

    try:
        venda = models.Venda(
            date=payload.date, client_id=payload.client_id, client_name=payload.client_name,
            total_value=payload.total_value, is_paid=payload.is_paid,
            payment_method=payload.payment_method, delivery_status=payload.delivery_status,
        )
        db.add(venda)
        db.flush()

        for item in payload.items:
            product = db.query(models.Product).filter(models.Product.id == item.product_id).first()

            item_cost = 0.0
            if product:
                item_cost = _consume_fifo(db, product, item.quantity)
                product.stock -= item.quantity
                db.flush()
                recalculate_average_cost(product, db)

            unit_cost = (item_cost / item.quantity) if item.quantity else 0.0
            profit = item.total_price - item_cost

            db.add(models.VendaItem(
                venda_id=venda.id, product_id=item.product_id, product_name=item.product_name,
                quantity=item.quantity, unit_price=item.unit_price, total_price=item.total_price,
                unit_cost=round(unit_cost, 4), profit=round(profit, 2),
            ))

        if not payload.is_paid and payload.client_id:
            client = db.query(models.Client).filter(models.Client.id == payload.client_id).first()
            if client:
                for item in payload.items:
                    db.add(models.Debt(
                        client_id=client.id, date=payload.date, product_name=item.product_name,
                        quantity=item.quantity, unit_price=item.unit_price, total_price=item.total_price,
                    ))

        db.commit()
        db.refresh(venda)
        return venda

    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao finalizar a venda.")


@router.patch("/{venda_id}/entregar", response_model=schemas.VendaOut)
def marcar_como_entregue(venda_id: int, db: Session = Depends(get_db)):
    venda = (
        db.query(models.Venda)
        .options(joinedload(models.Venda.items))
        .filter(models.Venda.id == venda_id)
        .first()
    )
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada.")

    venda.delivery_status = "ENTREGUE"
    db.commit()
    db.refresh(venda)
    return venda