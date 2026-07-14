from . import models, security
from .database import SessionLocal


def run() -> None:
    """Popula dados iniciais (usuário admin + exemplos) se o banco estiver vazio.
    Seguro para chamar em todo startup: só insere se as tabelas estiverem vazias.
    """
    db = SessionLocal()
    try:
        if not db.query(models.User).first():
            db.add(models.User(
                name="Administrador",
                email="admin@sistema.com",
                hashed_password=security.get_password_hash("123456"),
            ))

        if not db.query(models.Product).first():
            db.add_all([
                models.Product(name="Óleo de Motor 5W30", sku="OL-5W30", cost_price=25.00, sell_price=45.90, stock=120),
                models.Product(name="Filtro de Ar", sku="FIL-AR-01", cost_price=12.00, sell_price=25.50, stock=5),
                models.Product(name="Pastilha de Freio", sku="FRE-PAS-09", cost_price=60.00, sell_price=110.00, stock=34),
            ])

        if not db.query(models.Client).first():
            client = models.Client(
                name="Roberto Silva",
                document="111.222.333-44",
                phone="(11) 99999-9999",
                email="roberto@email.com",
                pix="roberto@email.com",
                zip_code="01001-000",
                address="Praça da Sé",
                number="123",
                neighborhood="Centro",
                city="São Paulo",
                state="SP",
                notes="Cliente antigo. Paga sempre no dia 10.",
            )
            db.add(client)
            db.flush()  # garante client.id sem precisar de commit

            db.add_all([
                models.Debt(client_id=client.id, date="10/07/2026", product_name="Óleo de Motor 5W30",
                            quantity=1, unit_price=45.00, total_price=45.00),
                models.Debt(client_id=client.id, date="12/07/2026", product_name="Filtro de Ar",
                            quantity=1, unit_price=20.00, total_price=20.00),
            ])

        db.commit()
    finally:
        db.close()
