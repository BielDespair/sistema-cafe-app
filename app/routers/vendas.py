from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(
    prefix="/vendas",
    tags=["Vendas"],
    dependencies=[Depends(security.get_current_user)],
)


def _allocate_from_lots(
    db: Session, product: models.Product, quantity_needed: int
) -> List[Tuple[models.StockLot, int]]:
    """Planeja quais lotes (mais antigos primeiro) cobrem `quantity_needed`
    unidades. NÃO grava nada e NUNCA inventa custo — se os lotes disponíveis
    não cobrirem tudo, o plano simplesmente vem menor que o pedido, e quem
    chama decide o que fazer com a parte não coberta (vira venda sob
    encomenda, pendente de custo)."""
    lots = (
        db.query(models.StockLot)
        .filter(models.StockLot.product_id == product.id, models.StockLot.quantity_remaining > 0)
        .order_by(models.StockLot.date.asc(), models.StockLot.id.asc())
        .all()
    )

    plano: List[Tuple[models.StockLot, int]] = []
    faltando = quantity_needed
    for lot in lots:
        if faltando <= 0:
            break
        consumida = min(lot.quantity_remaining, faltando)
        if consumida > 0:
            plano.append((lot, consumida))
            faltando -= consumida

    return plano


def _aplicar_alocacoes(
    db: Session,
    venda_item: models.VendaItem,
    plano: List[Tuple[models.StockLot, int]],
    data: str,
) -> None:
    """Executa o plano de alocação: reduz o saldo dos lotes, cria os registros
    de StockAllocation (anexados à *coleção* do item, não só gravados via FK
    solta — isso mantém `venda_item.allocations` correto em memória sem
    precisar de um refresh) e recalcula o status/custo/lucro do item."""
    alocado_agora = 0
    for lot, consumida in plano:
        lot.quantity_remaining -= consumida
        venda_item.allocations.append(models.StockAllocation(
            stock_lot_id=lot.id,
            quantity=consumida,
            unit_cost=lot.unit_cost,
            date=data,
        ))
        alocado_agora += consumida

    venda_item.quantity_allocated += alocado_agora

    if venda_item.quantity_allocated >= venda_item.quantity:
        total_custo = sum(a.quantity * a.unit_cost for a in venda_item.allocations)
        venda_item.unit_cost = round(total_custo / venda_item.quantity, 4)
        venda_item.profit = round(venda_item.total_price - total_custo, 2)
        venda_item.cost_status = "COMPLETO"
    elif venda_item.quantity_allocated > 0:
        venda_item.cost_status = "PARCIAL"
        venda_item.unit_cost = None
        venda_item.profit = None
    else:
        venda_item.cost_status = "PENDENTE"
        venda_item.unit_cost = None
        venda_item.profit = None


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

        for item_in in payload.items:
            venda_item = models.VendaItem(
                venda_id=venda.id, product_id=item_in.product_id, product_name=item_in.product_name,
                quantity=item_in.quantity, unit_price=item_in.unit_price, total_price=item_in.total_price,
            )
            db.add(venda_item)
            db.flush()

            product = db.query(models.Product).filter(models.Product.id == item_in.product_id).first()
            if product:
                # Estoque continua podendo ficar negativo — é o sinal de "venda sob
                # encomenda" que o app já usava, sem mudança nesse comportamento.
                product.stock -= item_in.quantity

                plano = _allocate_from_lots(db, product, item_in.quantity)
                _aplicar_alocacoes(db, venda_item, plano, payload.date)
            # Se o produto não existe mais (não deveria acontecer), o item fica
            # como PENDENTE — nunca inventamos custo.

        if not payload.is_paid and payload.client_id:
            client = db.query(models.Client).filter(models.Client.id == payload.client_id).first()
            if client:
                for item_in in payload.items:
                    db.add(models.Debt(
                        client_id=client.id, date=payload.date, product_name=item_in.product_name,
                        quantity=item_in.quantity, unit_price=item_in.unit_price, total_price=item_in.total_price,
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
