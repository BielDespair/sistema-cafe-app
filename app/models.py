from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    sku = Column(String, unique=True, index=True, nullable=False)
    cost_price = Column(Float, nullable=False, default=0)   # Custo médio — só para exibição/referência
    sell_price = Column(Float, nullable=False, default=0)
    stock = Column(Integer, nullable=False, default=0)      # Pode ficar negativo (venda sob encomenda)
    image_url = Column(String, nullable=True)               # Caminho relativo, ex: /uploads/products/3-a1b2c3d4.jpg

    lots = relationship("StockLot", back_populates="product", cascade="all, delete-orphan")


class StockLot(Base):
    """Lote de estoque para custo PEPS/FIFO.

    Cada entrada (compra) ou estoque inicial de um produto vira um lote com
    sua própria data e custo unitário. Ao vender, consumimos dos lotes mais
    antigos primeiro (`date`/`id` crescente) — isso dá o lucro real de cada
    venda, em vez de um custo médio que "mistura" preços de compras diferentes.
    """
    __tablename__ = "stock_lots"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    entrada_id = Column(Integer, ForeignKey("entradas.id"), nullable=True)
    date = Column(String, nullable=False)
    quantity_received = Column(Integer, nullable=False)
    quantity_remaining = Column(Integer, nullable=False)
    unit_cost = Column(Float, nullable=False)

    product = relationship("Product", back_populates="lots")


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    document = Column(String, default="")
    phone = Column(String, default="")
    email = Column(String, default="")
    pix = Column(String, default="")
    zip_code = Column(String, default="")
    address = Column(String, default="")
    number = Column(String, default="")
    neighborhood = Column(String, default="")
    city = Column(String, default="")
    state = Column(String, default="")
    notes = Column(Text, default="")

    debts = relationship("Debt", back_populates="client", cascade="all, delete-orphan")


class Debt(Base):
    """Um item de dívida (fiado) gerado por uma venda não paga."""
    __tablename__ = "debts"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    date = Column(String, nullable=False)
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)

    client = relationship("Client", back_populates="debts")


class Entrada(Base):
    """Registro de entrada de mercadoria (compra de estoque)."""
    __tablename__ = "entradas"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)


class Venda(Base):
    __tablename__ = "vendas"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    client_name = Column(String, nullable=False)
    total_value = Column(Float, nullable=False)
    is_paid = Column(Boolean, nullable=False, default=True)
    payment_method = Column(String, default="")
    delivery_status = Column(String, default="ENTREGUE")

    items = relationship("VendaItem", back_populates="venda", cascade="all, delete-orphan")


class VendaItem(Base):
    __tablename__ = "venda_items"

    id = Column(Integer, primary_key=True, index=True)
    venda_id = Column(Integer, ForeignKey("vendas.id"), nullable=False)
    product_id = Column(Integer, nullable=False)
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)       # preço de venda (o que o cliente pagou)
    total_price = Column(Float, nullable=False)
    unit_cost = Column(Float, nullable=False, default=0)   # custo PEPS aplicado nesta venda
    profit = Column(Float, nullable=False, default=0)      # total_price - (unit_cost * quantity)

    venda = relationship("Venda", back_populates="items")
