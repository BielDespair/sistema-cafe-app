import os
import uuid
from datetime import date
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(
    prefix="/products",
    tags=["Produtos"],
    dependencies=[Depends(security.get_current_user)],
)

UPLOAD_DIR = os.path.join("uploads", "products")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_SIZE_MB = 5


@router.get("", response_model=List[schemas.ProductOut])
def list_products(db: Session = Depends(get_db)):
    return db.query(models.Product).order_by(models.Product.name).all()


@router.post("", response_model=schemas.ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(payload: schemas.ProductCreate, db: Session = Depends(get_db)):
    if db.query(models.Product).filter(models.Product.sku == payload.sku).first():
        raise HTTPException(status_code=409, detail="Já existe um produto com esse SKU.")

    product = models.Product(**payload.model_dump())
    db.add(product)
    db.flush()

    if product.stock > 0:
        db.add(models.StockLot(
            product_id=product.id,
            entrada_id=None,
            date=date.today().isoformat(),
            quantity_received=product.stock,
            quantity_remaining=product.stock,
            unit_cost=product.cost_price,
        ))

    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: int, payload: schemas.ProductUpdate, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    duplicate = (
        db.query(models.Product)
        .filter(models.Product.sku == payload.sku, models.Product.id != product_id)
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Já existe outro produto com esse SKU.")

    # payload não inclui image_url — a foto é gerenciada só pelos endpoints
    # de upload/remoção abaixo, então editar aqui nunca apaga a foto por acidente.
    for field, value in payload.model_dump().items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    tem_entrada = db.query(models.Entrada).filter(models.Entrada.product_id == product_id).first()
    tem_venda = db.query(models.VendaItem).filter(models.VendaItem.product_id == product_id).first()

    if tem_entrada or tem_venda:
        raise HTTPException(
            status_code=409,
            detail=(
                "Esse produto já tem entradas ou vendas registradas e não pode ser apagado, "
                "para não perder o histórico. Se ele saiu de linha, deixe o estoque em 0 "
                "em vez de excluir."
            ),
        )

    _remove_image_file(product.image_url)
    db.query(models.StockLot).filter(models.StockLot.product_id == product_id).delete()

    db.delete(product)
    db.commit()


def _remove_image_file(image_url: str | None) -> None:
    """Apaga o arquivo de imagem do disco, se existir. Nunca deixa um erro de
    arquivo travar a operação principal (produto continua sendo salvo/apagado
    mesmo que a limpeza do arquivo antigo falhe por algum motivo)."""
    if not image_url:
        return
    filepath = image_url.lstrip("/")  # "/uploads/products/x.jpg" -> "uploads/products/x.jpg"
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except OSError:
        pass


@router.post("/{product_id}/imagem", response_model=schemas.ProductOut)
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Envie uma imagem JPG, PNG ou WEBP.")

    contents = await file.read()
    if len(contents) > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Imagem muito grande (máximo {MAX_IMAGE_SIZE_MB}MB).")

    _remove_image_file(product.image_url)

    filename = f"{product_id}-{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    product.image_url = f"/uploads/products/{filename}"
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}/imagem", response_model=schemas.ProductOut)
def remove_product_image(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    _remove_image_file(product.image_url)
    product.image_url = None
    db.commit()
    db.refresh(product)
    return product
