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
    image_url = Column(String, nullable=True)

    lots = relationship("StockLot", back_populates="product", cascade="all, delete-orphan")


class StockLot(Base):
    """Lote de estoque para custo PEPS/FIFO.

    Cada entrada (compra) ou estoque inicial de um produto vira um lote com
    sua própria data e custo unitário. Vendas consomem dos lotes mais antigos
    primeiro (`date`/`id` crescente) via StockAllocation — nunca diretamente.
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
    allocations = relationship("StockAllocation", back_populates="stock_lot")


class StockAllocation(Base):
    """Registra qual lote (StockLot) cobriu qual parte de qual item de venda.

    Existe pra suportar venda sob encomenda: uma StockAllocation só é criada
    quando existe estoque de verdade cobrindo aquela quantidade — seja no
    momento da venda (se já havia lote com saldo) ou depois, quando uma
    entrada nova chega e "quita" o custo de uma venda que ficou pendente.
    Uma linha de venda pode ter várias alocações (de lotes diferentes) até
    ficar 100% coberta.
    """
    __tablename__ = "stock_allocations"

    id = Column(Integer, primary_key=True, index=True)
    venda_item_id = Column(Integer, ForeignKey("venda_items.id"), nullable=False)
    stock_lot_id = Column(Integer, ForeignKey("stock_lots.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Float, nullable=False)   # custo do lote, congelado no momento da alocação
    date = Column(String, nullable=False)       # quando a alocação ocorreu (pode ser bem depois da venda)

    venda_item = relationship("VendaItem", back_populates="allocations")
    stock_lot = relationship("StockLot", back_populates="allocations")


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
    unit_price = Column(Float, nullable=False)       # preço de venda (o que o cliente pagou/vai pagar)
    total_price = Column(Float, nullable=False)

    # --- Rastreamento de custo real via lotes (PEPS), suporta venda sob encomenda ---
    quantity_allocated = Column(Integer, nullable=False, default=0)   # quanto já foi coberto por algum lote
    cost_status = Column(String, nullable=False, default="PENDENTE")  # PENDENTE | PARCIAL | COMPLETO
    unit_cost = Column(Float, nullable=True)   # só definitivo quando cost_status == "COMPLETO"
    profit = Column(Float, nullable=True)      # idem

    venda = relationship("Venda", back_populates="items")
    allocations = relationship("StockAllocation", back_populates="venda_item", cascade="all, delete-orphan")
