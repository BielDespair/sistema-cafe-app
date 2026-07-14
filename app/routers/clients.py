from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(
    prefix="/clients",
    tags=["Clientes"],
    dependencies=[Depends(security.get_current_user)],
)


def _to_out(client: models.Client) -> schemas.ClientOut:
    total_debt = sum(d.total_price for d in client.debts)
    return schemas.ClientOut(
        id=client.id,
        name=client.name,
        document=client.document,
        phone=client.phone,
        email=client.email,
        pix=client.pix,
        zip_code=client.zip_code,
        address=client.address,
        number=client.number,
        neighborhood=client.neighborhood,
        city=client.city,
        state=client.state,
        notes=client.notes,
        total_debt=total_debt,
        debts=[
            schemas.DebtOut(
                id=str(d.id), date=d.date, product_name=d.product_name,
                quantity=d.quantity, unit_price=d.unit_price, total_price=d.total_price,
            )
            for d in client.debts
        ],
    )


@router.get("", response_model=List[schemas.ClientOut])
def list_clients(db: Session = Depends(get_db)):
    clients = (
        db.query(models.Client)
        .options(joinedload(models.Client.debts))
        .order_by(models.Client.name)
        .all()
    )
    return [_to_out(c) for c in clients]


@router.post("", response_model=schemas.ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(payload: schemas.ClientCreate, db: Session = Depends(get_db)):
    client = models.Client(**payload.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return _to_out(client)


@router.put("/{client_id}", response_model=schemas.ClientOut)
def update_client(client_id: int, payload: schemas.ClientUpdate, db: Session = Depends(get_db)):
    client = (
        db.query(models.Client)
        .options(joinedload(models.Client.debts))
        .filter(models.Client.id == client_id)
        .first()
    )
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    for field, value in payload.model_dump().items():
        setattr(client, field, value)

    db.commit()
    db.refresh(client)
    return _to_out(client)


@router.post("/{client_id}/quitar-divida", response_model=schemas.ClientOut)
def quitar_divida(client_id: int, db: Session = Depends(get_db)):
    """Sugestão de melhoria: endpoint para dar baixa em todas as dívidas do
    cliente quando ele pagar o fiado acumulado."""
    client = (
        db.query(models.Client)
        .options(joinedload(models.Client.debts))
        .filter(models.Client.id == client_id)
        .first()
    )
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    for debt in list(client.debts):
        db.delete(debt)

    db.commit()
    db.refresh(client)
    return _to_out(client)
