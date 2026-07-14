from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(
    prefix="/entradas",
    tags=["Entradas"],
    dependencies=[Depends(security.get_current_user)],
)


@router.get("", response_model=List[schemas.EntradaOut])
def list_entradas(db: Session = Depends(get_db)):
    return db.query(models.Entrada).order_by(models.Entrada.id.desc()).all()


@router.post("", response_model=schemas.EntradaOut, status_code=status.HTTP_201_CREATED)
def registrar_entrada(payload: schemas.EntradaCreate, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == payload.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    total_cost = round(payload.quantity * payload.unit_cost, 2)

    # Custo médio ponderado: (valor em estoque atual + valor da nova compra) / novo estoque total
    current_total_value = product.cost_price * product.stock
    new_total_value = current_total_value + total_cost
    new_stock = product.stock + payload.quantity

    product.cost_price = (new_total_value / new_stock) if new_stock > 0 else product.cost_price
    product.stock = new_stock

    entrada = models.Entrada(
        date=payload.date,
        product_id=product.id,
        product_name=product.name,
        quantity=payload.quantity,
        unit_cost=payload.unit_cost,
        total_cost=total_cost,
    )
    db.add(entrada)
    db.commit()
    db.refresh(entrada)
    return entrada
