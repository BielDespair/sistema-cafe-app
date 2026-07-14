import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import seed
from .database import Base, engine
from .routers import auth, cep, clients, entradas, products, vendas

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Controle de Estoque API",
    description="API para o sistema de vendas, estoque, clientes e entradas.",
    version="1.0.0",
)

allowed_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://localhost:4173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins= ["*"], #allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(clients.router)
app.include_router(entradas.router)
app.include_router(vendas.router)
app.include_router(cep.router)

# Popula usuário admin e dados de exemplo se o banco estiver vazio (idempotente).
seed.run()


@app.get("/health", tags=["Sistema"])
def health_check():
    return {"status": "ok"}
