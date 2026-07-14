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
    cost_price = Column(Float, nullable=False, default=0)   # Custo médio ponderado
    sell_price = Column(Float, nullable=False, default=0)
    stock = Column(Integer, nullable=False, default=0)      # Pode ficar negativo (venda sob encomenda)


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
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)

    venda = relationship("Venda", back_populates="items")
