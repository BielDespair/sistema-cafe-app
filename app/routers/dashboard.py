from datetime import date, timedelta
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(security.get_current_user)],
)


def _resolve_period(preset: Optional[str], start: Optional[str], end: Optional[str]) -> Tuple[str, str]:
    today = date.today()

    if start and end:
        return start, end

    if preset == "7d":
        return (today - timedelta(days=6)).isoformat(), today.isoformat()
    if preset == "30d":
        return (today - timedelta(days=29)).isoformat(), today.isoformat()
    if preset == "this_week":
        start_of_week = today - timedelta(days=today.weekday())
        return start_of_week.isoformat(), today.isoformat()
    if preset == "last_week":
        start_of_this_week = today - timedelta(days=today.weekday())
        start_of_last_week = start_of_this_week - timedelta(days=7)
        end_of_last_week = start_of_this_week - timedelta(days=1)
        return start_of_last_week.isoformat(), end_of_last_week.isoformat()
    if preset == "this_month":
        return today.replace(day=1).isoformat(), today.isoformat()
    if preset == "last_month":
        first_this_month = today.replace(day=1)
        last_month_end = first_this_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return last_month_start.isoformat(), last_month_end.isoformat()

    return today.isoformat(), today.isoformat()


def _last_n_days(n: int, today: date) -> List[str]:
    return [(today - timedelta(days=i)).isoformat() for i in range(n - 1, -1, -1)]


def _last_n_months(n: int, today: date) -> List[str]:
    months = []
    year, month = today.year, today.month
    for _ in range(n):
        months.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(months))


@router.get("/summary", response_model=schemas.DashboardSummary)
def get_summary(
    preset: Optional[str] = Query(
        None, description="today|7d|30d|this_week|last_week|this_month|last_month"
    ),
    start: Optional[str] = Query(None, description="YYYY-MM-DD, usado com `end`"),
    end: Optional[str] = Query(None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    start_date, end_date = _resolve_period(preset, start, end)

    vendas = (
        db.query(models.Venda)
        .options(joinedload(models.Venda.items))
        .filter(models.Venda.date >= start_date, models.Venda.date <= end_date)
        .all()
    )

    todos_itens = [item for v in vendas for item in v.items]
    itens_completos = [i for i in todos_itens if i.cost_status == "COMPLETO"]
    itens_pendentes = [i for i in todos_itens if i.cost_status != "COMPLETO"]

    # Faturamento é sempre o valor real da venda (o cliente se comprometeu a
    # pagar isso, independente de já sabermos o custo ou não).
    revenue = sum(v.total_value for v in vendas)

    # Custo e lucro só contam o que já está confirmado (evita "inventar"
    # lucro/prejuízo de vendas sob encomenda ainda sem custo real).
    cost = sum(i.unit_cost * i.quantity for i in itens_completos)
    profit = sum(i.profit for i in itens_completos)

    # Mostrado separado no dashboard — nunca somado ao lucro.
    pending_cost_revenue = sum(i.total_price for i in itens_pendentes)

    units_sold = sum(item.quantity for item in todos_itens)
    sales_count = len(vendas)
    average_ticket = (revenue / sales_count) if sales_count else 0.0

    return schemas.DashboardSummary(
        start_date=start_date,
        end_date=end_date,
        revenue=round(revenue, 2),
        cost=round(cost, 2),
        profit=round(profit, 2),
        pending_cost_revenue=round(pending_cost_revenue, 2),
        sales_count=sales_count,
        units_sold=units_sold,
        average_ticket=round(average_ticket, 2),
    )


@router.get("/low-stock", response_model=List[schemas.LowStockProduct])
def get_low_stock(threshold: int = Query(10, ge=0), db: Session = Depends(get_db)):
    products = (
        db.query(models.Product)
        .filter(models.Product.stock <= threshold)
        .order_by(models.Product.stock.asc())
        .all()
    )
    return [
        schemas.LowStockProduct(
            id=p.id, name=p.name, sku=p.sku, stock=p.stock, sell_price=p.sell_price,
            status="SEM_ESTOQUE" if p.stock <= 0 else "BAIXO",
        )
        for p in products
    ]


@router.get("/devedores", response_model=List[schemas.DevedorOut])
def get_devedores(db: Session = Depends(get_db)):
    clients = db.query(models.Client).options(joinedload(models.Client.debts)).all()

    devedores = []
    for c in clients:
        total = sum(d.total_price for d in c.debts)
        if total > 0:
            oldest = min((d.date for d in c.debts), default=None)
            devedores.append(schemas.DevedorOut(
                id=c.id, name=c.name, phone=c.phone, notes=c.notes,
                total_debt=round(total, 2), oldest_debt_date=oldest,
                debts=[
                    schemas.DebtOut(
                        id=str(d.id), date=d.date, product_name=d.product_name,
                        quantity=d.quantity, unit_price=d.unit_price, total_price=d.total_price,
                    )
                    for d in c.debts
                ],
            ))

    devedores.sort(key=lambda d: d.total_debt, reverse=True)
    return devedores


@router.get("/entregas-pendentes", response_model=List[schemas.EntregaPendenteOut])
def get_entregas_pendentes(db: Session = Depends(get_db)):
    vendas = (
        db.query(models.Venda)
        .options(joinedload(models.Venda.items))
        .filter(models.Venda.delivery_status == "PENDENTE")
        .order_by(models.Venda.date.asc())
        .all()
    )

    result = []
    for v in vendas:
        phone = ""
        if v.client_id:
            client = db.query(models.Client).filter(models.Client.id == v.client_id).first()
            if client:
                phone = client.phone

        items_summary = ", ".join(f"{item.quantity}x {item.product_name}" for item in v.items)

        result.append(schemas.EntregaPendenteOut(
            id=v.id, date=v.date, client_id=v.client_id, client_name=v.client_name,
            client_phone=phone, total_value=v.total_value, items_summary=items_summary,
        ))

    return result


@router.get("/top-clientes", response_model=List[schemas.TopClienteOut])
def get_top_clientes(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    vendas = db.query(models.Venda).filter(models.Venda.client_id.isnot(None)).all()

    agregados: dict = {}
    for v in vendas:
        info = agregados.setdefault(
            v.client_id, {"total": 0.0, "count": 0, "last_date": v.date, "name": v.client_name}
        )
        info["total"] += v.total_value
        info["count"] += 1
        if v.date > info["last_date"]:
            info["last_date"] = v.date

    clients_by_id = {c.id: c for c in db.query(models.Client).all()}

    ranking = []
    for client_id, info in agregados.items():
        client = clients_by_id.get(client_id)
        ranking.append(schemas.TopClienteOut(
            id=client_id,
            name=info["name"],
            phone=client.phone if client else "",
            notes=client.notes if client else "",
            total_comprado=round(info["total"], 2),
            quantidade_compras=info["count"],
            ultima_compra=info["last_date"],
        ))

    ranking.sort(key=lambda r: r.total_comprado, reverse=True)
    return ranking[:limit]


@router.get("/top-produtos", response_model=List[schemas.TopProdutoOut])
def get_top_produtos(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    items = db.query(models.VendaItem).all()

    agregados: dict = {}
    for item in items:
        info = agregados.setdefault(
            item.product_id, {"name": item.product_name, "qty": 0, "revenue": 0.0, "profit": 0.0}
        )
        info["qty"] += item.quantity
        info["revenue"] += item.total_price
        # Só soma lucro confirmado — itens ainda pendentes de custo entram no
        # ranking de quantidade/faturamento normalmente, só não distorcem o lucro.
        if item.cost_status == "COMPLETO" and item.profit is not None:
            info["profit"] += item.profit

    ranking = [
        schemas.TopProdutoOut(
            product_id=pid, product_name=info["name"],
            quantidade_vendida=info["qty"],
            faturamento=round(info["revenue"], 2),
            lucro=round(info["profit"], 2),
        )
        for pid, info in agregados.items()
    ]
    ranking.sort(key=lambda r: r.quantidade_vendida, reverse=True)
    return ranking[:limit]


@router.get("/profit-series", response_model=List[schemas.ProfitPoint])
def get_profit_series(
    preset: str = Query("30d", description="7d|30d|12m"),
    db: Session = Depends(get_db),
):
    today = date.today()
    group_by_month = preset == "12m"

    if group_by_month:
        labels = _last_n_months(12, today)
        start_date = f"{labels[0]}-01"
    else:
        days = 7 if preset == "7d" else 30
        labels = _last_n_days(days, today)
        start_date = labels[0]

    vendas = (
        db.query(models.Venda)
        .options(joinedload(models.Venda.items))
        .filter(models.Venda.date >= start_date)
        .all()
    )

    buckets = {label: {"revenue": 0.0, "cost": 0.0, "profit": 0.0} for label in labels}
    for v in vendas:
        label = v.date[:7] if group_by_month else v.date
        if label not in buckets:
            continue

        buckets[label]["revenue"] += v.total_value  # faturamento bruto, sempre real

        for item in v.items:
            # Só soma custo/lucro de itens com custo já confirmado — senão o
            # gráfico mostraria lucro maior do que existe de verdade em meses
            # com venda sob encomenda ainda não reposta.
            if item.cost_status == "COMPLETO" and item.unit_cost is not None and item.profit is not None:
                buckets[label]["cost"] += item.unit_cost * item.quantity
                buckets[label]["profit"] += item.profit

    return [
        schemas.ProfitPoint(
            label=label,
            revenue=round(buckets[label]["revenue"], 2),
            cost=round(buckets[label]["cost"], 2),
            profit=round(buckets[label]["profit"], 2),
        )
        for label in labels
    ]
