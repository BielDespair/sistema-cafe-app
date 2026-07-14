# Controle de Estoque — API (FastAPI)

API em Python que substitui os serviços mockados (`authService`, `productService`,
`clientService`, `entradaService`, `vendaService`, `cepService`) por um backend
real, com banco de dados persistente e a mesma lógica de negócio do frontend.

## Como rodar

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env             # ajuste SECRET_KEY antes de ir para produção

uvicorn app.main:app --reload --port 8000
```

Na primeira execução o banco SQLite (`estoque.db`) é criado automaticamente e
populado com:
- usuário `admin@sistema.com` / senha `123456`
- os 3 produtos de exemplo
- o cliente "Roberto Silva" com as 2 dívidas de exemplo

Documentação interativa (Swagger) em: `http://localhost:8000/docs`

## Conectando o frontend React

Troque as implementações mockadas dos arquivos em `services/` por chamadas
`fetch`/`axios` para `http://localhost:8000`, mandando o header
`Authorization: Bearer <token>` (token retornado por `POST /auth/login`) em
todas as rotas exceto `/auth/login`. Os campos JSON continuam em camelCase
(`sellPrice`, `zipCode`, `totalDebt`...), então as interfaces TypeScript que
você já tem não precisam mudar — se quiser, eu faço essa troca nos arquivos de
`services/` na próxima mensagem.

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| POST | `/auth/login` | Autentica e retorna `{ token, user }` |
| GET | `/auth/me` | Dados do usuário logado |
| GET | `/products` | Lista produtos |
| POST | `/products` | Cria produto |
| PUT | `/products/{id}` | Atualiza produto |
| DELETE | `/products/{id}` | Remove produto |
| GET | `/clients` | Lista clientes (com dívidas) |
| POST | `/clients` | Cria cliente |
| PUT | `/clients/{id}` | Atualiza cliente |
| POST | `/clients/{id}/quitar-divida` | Zera as dívidas do cliente (novo) |
| GET | `/entradas` | Lista entradas de estoque |
| POST | `/entradas` | Registra entrada (recalcula custo médio) |
| GET | `/vendas` | Lista vendas |
| POST | `/vendas` | Registra venda (baixa estoque + gera fiado) |
| GET | `/cep/{cep}` | Proxy para ViaCEP |
| GET | `/health` | Health check |

Todas as rotas, exceto `/auth/login` e `/health`, exigem o header
`Authorization: Bearer <token>`.

## O que mudou em relação ao mock (e por quê)

- **Persistência real** (SQLite por padrão, troque `DATABASE_URL` para Postgres
  em produção): os dados não somem mais a cada reload do servidor.
- **Senha com hash (bcrypt) + JWT de verdade**, em vez de usuário/senha fixos
  no código — o `authService` original tinha as credenciais expostas em texto
  puro no frontend, o que não é seguro nem escalável para múltiplos usuários.
- **Registro de venda é atômico**: baixa de estoque + criação da dívida
  acontecem na mesma transação (`db.commit()`/`db.rollback()`), então uma
  falha no meio do processo não deixa o estoque ou a dívida "pela metade".
- **Validação de entrada com Pydantic** (preços não-negativos, quantidade > 0,
  SKU único) — o mock não validava nada antes de gravar.
- **CEP some por trás da API** (a chave/rota fica no backend), permitindo, se
  quiser, colocar cache ou rate limit sem tocar no frontend.

## Sugestões de melhoria (não implementadas, para você avaliar)

1. **Paginação e busca no backend** para `/clients` e `/products` — hoje a
   lista inteira volta de uma vez; se a base de clientes crescer, isso pesa a
   tela de vendas no tablet.
2. **Alembic para migrações** de banco, em vez de `create_all` — assim você
   consegue evoluir o schema em produção sem apagar dados.
3. **Refresh token** além do access token, já que 8h de validade é ok para um
   turno mas força re-login todo dia; um refresh evitaria isso sem deixar o
   token principal com validade longa demais.
4. **Trava de estoque configurável**: hoje, replicando o mock, a venda deixa o
   estoque ir negativo de propósito (para virar "lista de reposição"). Talvez
   valha um campo de configuração por produto ("permite venda sob encomenda?
   sim/não") em vez de ser sempre permitido.
5. **Idempotência no registro de venda**: se o tablet perder conexão no meio
   do "Finalizar Venda" e o app tentar de novo, hoje pode duplicar a venda. Um
   `client_request_id` enviado pelo frontend e checado no backend evitaria
   isso — importante para venda de rua com internet instável.
6. **Log de auditoria** simples (quem editou o quê e quando) em produtos e
   clientes, útil se mais de uma pessoa mexe no sistema.
7. **Testes automatizados** (pytest + `TestClient` do FastAPI) cobrindo pelo
   menos o fluxo de venda com fiado e o cálculo de custo médio, que são as
   partes com mais lógica de negócio.

Posso implementar qualquer um desses itens, ou já trocar os `services/*.ts` do
frontend para consumir esta API — é só pedir.
