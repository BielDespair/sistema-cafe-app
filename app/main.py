import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import seed
from .routers import auth, cep, clients, dashboard, entradas, products, vendas

# Nada de Base.metadata.create_all() aqui — desde que o Alembic entrou,
# quem cria/atualiza as tabelas é ele (`alembic upgrade head`), rodado antes
# da API subir (veja o Start Command no Render). Ter os dois mexendo no
# schema ao mesmo tempo é receita pra inconsistência.

app = FastAPI(
    title="Controle de Estoque API",
    description="API para o sistema de vendas, estoque, clientes e entradas.",
    version="1.3.0",
)

allowed_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve as fotos de produto enviadas por upload (ex: /uploads/products/3-a1b2.jpg)
os.makedirs(os.path.join("uploads", "products"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(clients.router)
app.include_router(entradas.router)
app.include_router(vendas.router)
app.include_router(cep.router)
app.include_router(dashboard.router)

# O seed continua rodando no startup — ele só insere dados de exemplo se as
# tabelas estiverem vazias, então é seguro mesmo com o schema vindo do Alembic
# (as tabelas já existem quando a API sobe, graças ao `alembic upgrade head`
# rodado antes).
seed.run()


@app.get("/health", tags=["Sistema"])
def health_check():
    return {"status": "ok"}