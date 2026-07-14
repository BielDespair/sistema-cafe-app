from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(
    prefix="/vendas",
    tags=["Vendas"],
    dependencies=[Depends(security.get_current_user)],
)


@router.get("", response_model=List[schemas.VendaOut])
def list_vendas(db: Session = Depends(get_db)):
    return (
        db.query(models.Venda)
        .options(joinedload(models.Venda.items))
        .order_by(models.Venda.id.desc())
        .all()
    )


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
            date=payload.date,
            client_id=payload.client_id,
            client_name=payload.client_name,
            total_value=payload.total_value,
            is_paid=payload.is_paid,
            payment_method=payload.payment_method,
            delivery_status=payload.delivery_status,
        )
        db.add(venda)
        db.flush()  # gera venda.id sem precisar commitar ainda

        for item in payload.items:
            db.add(models.VendaItem(
                venda_id=venda.id,
                product_id=item.product_id,
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
            ))

            # Dá baixa no estoque MESMO SE FICAR NEGATIVO (gera lista de reposição),
            # replicando o comportamento original do mock.
            product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
            if product:
                product.stock -= item.quantity

        if not payload.is_paid and payload.client_id:
            client = db.query(models.Client).filter(models.Client.id == payload.client_id).first()
            if client:
                for item in payload.items:
                    db.add(models.Debt(
                        client_id=client.id,
                        date=payload.date,
                        product_name=item.product_name,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        total_price=item.total_price,
                    ))

        db.commit()
        db.refresh(venda)
        return venda

    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao finalizar a venda.")
