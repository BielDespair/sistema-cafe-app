from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base para todo schema exposto pela API.

    Gera/aceita JSON em camelCase (sellPrice, zipCode, ...) para que o
    frontend React/TS não precise mudar nomes de campos.
    """
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


# ---------------- Auth ----------------

class LoginRequest(CamelModel):
    email: EmailStr
    password: str


class UserOut(CamelModel):
    id: int
    name: str


class LoginResponse(CamelModel):
    token: str
    user: UserOut


# ---------------- Produtos ----------------

class ProductBase(CamelModel):
    name: str
    sku: str
    cost_price: float = Field(ge=0)
    sell_price: float = Field(ge=0)
    stock: int = 0


class ProductCreate(ProductBase):
    pass


class ProductUpdate(ProductBase):
    pass


class ProductOut(ProductBase):
    id: int
    image_url: Optional[str] = None


# ---------------- Entradas ----------------

class EntradaUpdate(CamelModel):
    date: str
    quantity: int = Field(gt=0)
    unit_cost: float = Field(ge=0)


class EntradaCreate(CamelModel):
    date: str
    product_id: int
    quantity: int = Field(gt=0)
    unit_cost: float = Field(ge=0)


class EntradaOut(CamelModel):
    id: int
    date: str
    product_id: int
    product_name: str
    quantity: int
    unit_cost: float
    total_cost: float
    pode_editar: bool


# ---------------- Clientes / Dívidas ----------------

class DebtOut(CamelModel):
    id: str
    date: str
    product_name: str
    quantity: int
    unit_price: float
    total_price: float


class ClientBase(CamelModel):
    name: str
    document: str = ""
    phone: str = ""
    email: str = ""
    pix: str = ""
    zip_code: str = ""
    address: str = ""
    number: str = ""
    neighborhood: str = ""
    city: str = ""
    state: str = ""
    notes: str = ""


class ClientCreate(ClientBase):
    pass


class ClientUpdate(ClientBase):
    pass


class ClientOut(ClientBase):
    id: int
    total_debt: float
    debts: List[DebtOut] = []


# ---------------- Vendas ----------------

class VendaItemIn(CamelModel):
    product_id: int
    product_name: str
    quantity: int = Field(gt=0)
    unit_price: float = Field(ge=0)
    total_price: float = Field(ge=0)


class VendaCreate(CamelModel):
    date: str
    client_id: Optional[int] = None
    client_name: str
    items: List[VendaItemIn]
    total_value: float
    is_paid: bool
    payment_method: Literal["PIX", "DINHEIRO", "CARTAO", ""] = ""
    delivery_status: Literal["ENTREGUE", "PENDENTE"]


class VendaItemOut(CamelModel):
    id: int
    product_id: int
    product_name: str
    quantity: int
    unit_price: float
    total_price: float

    # Rastreamento de custo real via lotes PEPS — suporta venda sob encomenda.
    # unit_cost/profit só vêm preenchidos quando cost_status == "COMPLETO";
    # antes disso, o custo real ainda não existe e não deve ser inventado.
    quantity_allocated: int
    cost_status: Literal["PENDENTE", "PARCIAL", "COMPLETO"]
    unit_cost: Optional[float] = None
    profit: Optional[float] = None


class VendaOut(CamelModel):
    id: int
    date: str
    client_id: Optional[int] = None
    client_name: str
    items: List[VendaItemOut]
    total_value: float
    is_paid: bool
    payment_method: str
    delivery_status: str


# ---------------- CEP ----------------

class CepOut(CamelModel):
    cep: str
    logradouro: str
    bairro: str
    localidade: str
    uf: str


# ---------------- Dashboard ----------------

class DashboardSummary(CamelModel):
    start_date: str
    end_date: str
    revenue: float               # faturamento bruto (toda venda, sempre real)
    cost: float                  # custo PEPS confirmado (só itens com cost_status == "COMPLETO")
    profit: float                # lucro confirmado (idem)
    pending_cost_revenue: float  # valor de vendas cujo custo ainda não foi confirmado (aguardando reposição)
    sales_count: int
    units_sold: int
    average_ticket: float


class LowStockProduct(CamelModel):
    id: int
    name: str
    sku: str
    stock: int
    sell_price: float
    status: Literal["SEM_ESTOQUE", "BAIXO"]


class DevedorOut(CamelModel):
    id: int
    name: str
    phone: str
    notes: str = ""
    total_debt: float
    oldest_debt_date: Optional[str] = None
    debts: List[DebtOut] = []


class ProfitPoint(CamelModel):
    label: str
    revenue: float
    cost: float
    profit: float


class EntregaPendenteOut(CamelModel):
    id: int
    date: str
    client_id: Optional[int] = None
    client_name: str
    client_phone: str = ""
    total_value: float
    items_summary: str


class TopClienteOut(CamelModel):
    id: int
    name: str
    phone: str
    notes: str = ""
    total_comprado: float
    quantidade_compras: int
    ultima_compra: Optional[str] = None


class TopProdutoOut(CamelModel):
    product_id: int
    product_name: str
    quantidade_vendida: int
    faturamento: float
    lucro: float
