import re

import httpx
from fastapi import APIRouter, Depends, HTTPException

from .. import security

router = APIRouter(
    prefix="/cep",
    tags=["CEP"],
    dependencies=[Depends(security.get_current_user)],
)


@router.get("/{cep}", response_model=None)
async def buscar_cep(cep: str):
    clean_cep = re.sub(r"\D", "", cep)
    if len(clean_cep) != 8:
        raise HTTPException(status_code=400, detail="CEP inválido.")

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(f"https://viacep.com.br/ws/{clean_cep}/json/")
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError:
            raise HTTPException(status_code=502, detail="Erro ao consultar o serviço de CEP.")

    if data.get("erro"):
        raise HTTPException(status_code=404, detail="CEP não encontrado.")

    return data
