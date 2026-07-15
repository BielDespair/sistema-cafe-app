from . import models, security
from .database import SessionLocal


def run() -> None:
    db = SessionLocal()
    try:
        if not db.query(models.Product).first():
            seed_products = [
                ("Café Especial 250g Grão", "CE-250-GRAO", 12.00, 22.90, 0, "/uploads/products/especial_graos.webp"),
                ("Café Especial 250g Pó", "CE-250-PO", 11.50, 21.90, 0, "/uploads/products/especial_po.jpg"),
                ("Café Gourmet 500g", "CG-500", 18.00, 32.90, 0, "/uploads/products/gourmet.webp"),
                ("Café Tradicional 500g", "CT-500", 9.00, 16.90, 0, "/uploads/products/tradicional.webp"),
            ]
            for name, sku, cost, sell, stock in seed_products:
                product = models.Product(name=name, sku=sku, cost_price=cost, sell_price=sell, stock=stock)
                db.add(product)
                db.flush()
                db.add(models.StockLot(
                    product_id=product.id,
                    entrada_id=None,
                    date="2026-01-01",
                    quantity_received=stock,
                    quantity_remaining=stock,
                    unit_cost=cost,
                ))

        if not db.query(models.Client).first():
            client = models.Client(
                name="Roberto Silva", document="111.222.333-44", phone="(11) 99999-9999",
                email="roberto@email.com", pix="roberto@email.com", zip_code="01001-000",
                address="Praça da Sé", number="123", neighborhood="Centro", city="São Paulo", state="SP",
                notes="Cliente antigo. Paga sempre no dia 10.",
            )
            db.add(client)
            db.flush()

            db.add_all([
                models.Debt(client_id=client.id, date="10/07/2026", product_name="Café Especial 250g Grão",
                            quantity=1, unit_price=22.90, total_price=22.90),
                models.Debt(client_id=client.id, date="12/07/2026", product_name="Café Tradicional 500g",
                            quantity=1, unit_price=16.90, total_price=16.90),
            ])

        db.commit()
    finally:
        db.close()