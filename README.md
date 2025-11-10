BuildFlow

BuildFlow e um microsservico de processamento de pedidos de e-commerce, projetado com foco em alta performance e escalabilidade, simulando o backend de um grande "home center".

Este projeto foi desenvolvido como um portfolio tecnico para demonstrar competencias em arquiteturas modernas de backend. O core do sistema e uma API em Python (FastAPI) que garante baixa latencia na criacao de pedidos, utilizando um fluxo de processamento assincrono.

Como funciona
- Ao receber um pedido, a API o valida e o salva rapidamente no banco de dados.
- Em seguida, o enfileira para processamento em segundo plano (por exemplo: verificacao de estoque e pagamento).
- Essa abordagem libera o cliente imediatamente e torna o sistema mais resiliente e escalavel.

Pilares tecnicos
- Python/FastAPI
- Postgres (persistencia relacional)
- Redis (cache)
- RabbitMQ (filas)
- Docker e CI/CD
- Testes automatizados

Como rodar
- Pre-requisitos: Python 3.11+, pip e (opcional) Docker para Postgres.
- 1) Crie e ative um virtualenv (PowerShell):
  - `python -m venv .venv`
  - `./.venv/Scripts/Activate.ps1`
- 2) Instale dependencias:
  - `pip install -r requirements.txt`
- 3) Configure o banco de dados:
  - Opcao A (padrao/DEV): usar SQLite. Nao defina `DATABASE_URL`. Um arquivo `dev.db` sera criado automaticamente.
  - Opcao B (Postgres): suba um Postgres local (ex. via Docker) e defina `DATABASE_URL`.
    - Docker Postgres (exemplo):
      - `docker run --name buildflow-postgres -e POSTGRES_USER=dev -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=buildflow -p 5432:5432 -d postgres:16`
    - Definir `DATABASE_URL` (PowerShell - somente sessao atual):
      - `$env:DATABASE_URL = "postgresql://dev:dev@localhost:5432/buildflow"`
    - Definir `DATABASE_URL` (CMD - somente sessao atual):
      - `set DATABASE_URL=postgresql://dev:dev@localhost:5432/buildflow`
- 4) Suba o RabbitMQ (necessario para fila de pedidos). Exemplo usando Docker:
  - `docker run --name buildflow-rabbit -p 5672:5672 -p 15672:15672 -d rabbitmq:3-management`
  - (Opcional) Defina `RABBITMQ_URL` se quiser apontar para outra instancia (`amqp://user:pass@host:5672/vhost`). `PEDIDOS_QUEUE` define o nome da fila (padrao `pedidos`).
- 5) Suba o Redis para caching (opcional em dev, recomendado em prod). Exemplo usando Docker:
  - `docker run --name buildflow-redis -p 6379:6379 -d redis:7`
  - Ajuste `REDIS_URL` (`redis://host:6379/0`) e `PRODUTOS_CACHE_TTL` conforme necessidade.
- 6) Inicie o worker em um terminal dedicado:
  - `python worker.py`
- 7) Inicie a API em outro terminal:
  - `uvicorn main:app --reload`
- 8) Acesse a documentacao:
  - `http://127.0.0.1:8000/docs`

Endpoints
- `GET /produtos` — lista produtos
- `POST /pedidos` — cria um pedido
- `GET /pedidos/{pedido_id}` — consulta status/detalhe do pedido

FAQ
- Preciso instalar Postgres localmente? O pacote `psycopg2-binary` e apenas o driver do Python. Voce precisa de um servidor Postgres em execucao (local, Docker ou remoto). Se nao quiser usar Postgres em dev, o projeto funciona com SQLite por padrao.
- A variavel `DATABASE_URL` persiste? Nao. Em PowerShell/CMD, definir via `$env:`/`set` vale apenas para a sessao atual. Para persistir, adicione a variavel nas variaveis de ambiente do sistema ou crie um script de inicializacao. O formato `postgresql://user:pass@host:5432/dbname` e o DSN padrao do SQLAlchemy/Postgres — ajuste conforme seu ambiente.
- So preciso rodar `uvicorn main:app --reload`? Sim, apos instalar as dependencias e garantir que o banco (SQLite ou Postgres) esteja acessivel. As tabelas sao criadas automaticamente na inicializacao (ver `main.py:1`).

Rodar com Docker (Postgres + API)
- Passo unico: `docker compose up -d --build`
- Acesse a API: `http://127.0.0.1:8000/docs`
- Containers criados:
  - `buildflow-postgres` (Postgres 16)
  - `buildflow-redis` (Redis 7)
  - `buildflow-rabbit` (RabbitMQ 3 + console em `http://localhost:15672`)
  - `buildflow-api` (FastAPI/uvicorn)
  - `buildflow-worker` (processamento assíncrono de pedidos)

Testes
- Instalar dependências de teste (já no `requirements.txt`).
- Rodar: `pytest -q`
- O suite inclui:
  - Testes de unidade para cálculo de total (`app/services.py`).
  - Testes de integração dos endpoints via `TestClient`.
- Cada push é validado automaticamente via GitHub Actions (workflow `ci.yml` rodando `pytest`).
