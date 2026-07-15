from datetime import date
from pathlib import Path
import shutil
from typing import List
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db


UPLOAD_DIR = Path("uploads/products")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


router = APIRouter(
    prefix="/products",
    tags=["Produtos"],
    dependencies=[Depends(security.get_current_user)],
)


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

    # Se já nasce com estoque, cria um lote PEPS pra esse estoque inicial
    # poder ser consumido corretamente nas vendas. Esse é o ÚNICO lugar (além
    # de Entradas) onde estoque é definido a partir daqui pra frente.
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

    # ESTOQUE NUNCA É ALTERADO POR AQUI, de propósito — mesmo que o payload
    # traga um valor diferente. `product.stock` tem que ficar sempre em
    # sincronia com o saldo somado dos StockLot (é isso que sustenta o custo
    # PEPS e a venda sob encomenda). Só existem dois jeitos legítimos de mudar
    # estoque depois que o produto já existe:
    #   - pra cima: registrar uma Entrada (exige custo, cria lote de verdade)
    #   - pra baixo: uma Venda (ou, futuramente, um ajuste de perda/quebra)
    # Editar aqui serve só pra nome, SKU e preços.
    dados = payload.model_dump()
    dados.pop("stock", None)

    for field, value in dados.items():
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

    # Produto nunca usado: pode ter um lote de estoque inicial órfão, apaga junto.
    db.query(models.StockLot).filter(models.StockLot.product_id == product_id).delete()

    db.delete(product)
    db.commit()


@router.post("/{product_id}/imagem", response_model=schemas.ProductOut)
def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    product = (
        db.query(models.Product)
        .filter(models.Product.id == product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Produto não encontrado."
        )

    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/webp",
    }

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Formato de imagem inválido."
        )

    extension = Path(file.filename).suffix.lower()
    filename = f"{uuid.uuid4()}{extension}"

    filepath = UPLOAD_DIR / filename

    with filepath.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    product.image_url = f"/uploads/products/{filename}"

    db.commit()
    db.refresh(product)

    return product