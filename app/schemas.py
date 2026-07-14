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


# ---------------- Entradas ----------------

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


class VendaItemOut(VendaItemIn):
    id: int


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
