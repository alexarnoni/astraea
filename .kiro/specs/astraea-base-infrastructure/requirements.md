# Requirements Document

## Introduction

Infraestrutura base da plataforma Astraea, responsável por monitoramento de objetos próximos à Terra (NEOs) e eventos solares. Esta feature define a estrutura de contêineres, banco de dados, scripts de inicialização e scaffolding dos serviços collector e api, permitindo que o ambiente seja levantado com um único comando (`docker compose up -d`).

## Glossary

- **Astraea**: Plataforma de monitoramento de NEOs e eventos solares.
- **Collector**: Serviço Python responsável por coletar dados das APIs públicas da NASA.
- **API**: Serviço Python baseado em FastAPI que expõe os dados processados.
- **DB**: Serviço PostgreSQL 15 que armazena os dados brutos e processados.
- **Docker_Compose**: Orquestrador de contêineres utilizado para subir o ambiente local.
- **Init_Script**: Script SQL executado na inicialização do banco de dados.
- **Schema**: Namespace lógico dentro do PostgreSQL (raw, staging, mart).
- **NEO**: Near-Earth Object — objeto astronômico com órbita próxima à Terra.
- **NASA_API**: APIs públicas da NASA (NeoWs e DONKI) consumidas pelo Collector.
- **DATABASE_URL**: String de conexão PostgreSQL no formato `postgresql://user:pass@host:port/db`.
- **Healthcheck**: Verificação periódica do estado de saúde de um contêiner.

---

## Requirements

### Requirement 1: Orquestração de Contêineres

**User Story:** Como desenvolvedor, quero subir todos os serviços com um único comando, para que o ambiente de desenvolvimento e produção seja reproduzível.

#### Acceptance Criteria

1. THE Docker_Compose SHALL definir três serviços: db, collector e api.
2. WHEN o serviço db é iniciado, THE Docker_Compose SHALL aplicar um Healthcheck usando `pg_isready` para verificar a disponibilidade do banco.
3. WHEN o Healthcheck do db reporta estado saudável, THE Docker_Compose SHALL iniciar os serviços collector e api.
4. IF o serviço db não atingir estado saudável, THEN THE Docker_Compose SHALL manter collector e api no estado de espera.
5. THE Docker_Compose SHALL configurar restart policy `unless-stopped` para os serviços collector e api.
6. THE Docker_Compose SHALL utilizar um volume nomeado `astraea_pgdata` para persistência dos dados do db.

---

### Requirement 2: Serviço de Banco de Dados (db)

**User Story:** Como desenvolvedor, quero um serviço PostgreSQL 15 configurável via variáveis de ambiente, para que credenciais não sejam hardcoded no repositório.

#### Acceptance Criteria

1. THE DB SHALL utilizar a imagem `postgres:15-alpine`.
2. THE DB SHALL expor a porta 5432 do contêiner para a porta 5432 do host.
3. WHEN o DB é iniciado, THE DB SHALL ler as variáveis `POSTGRES_USER`, `POSTGRES_PASSWORD` e `POSTGRES_DB` a partir do arquivo `.env`.
4. THE DB SHALL montar o volume `astraea_pgdata` no caminho `/var/lib/postgresql/data`.

---

### Requirement 3: Serviço Collector

**User Story:** Como desenvolvedor, quero um serviço de coleta de dados isolado em contêiner, para que a lógica de ingestão seja independente dos demais serviços.

#### Acceptance Criteria

1. THE Collector SHALL ser construído a partir de um Dockerfile localizado em `./collector`.
2. THE Collector SHALL receber as variáveis de ambiente `DATABASE_URL` e `NASA_API_KEY`.
3. WHEN o Collector é iniciado, THE Collector SHALL executar o arquivo `main.py` como ponto de entrada.
4. THE Collector SHALL utilizar a imagem base `python:3.11-slim` e instalar dependências a partir de `requirements.txt`.
5. THE `collector/main.py` placeholder SHALL conter um loop infinito com `time.sleep(3600)` para evitar que o contêiner encerre imediatamente e entre em restart loop antes da lógica de coleta ser implementada.

---

### Requirement 4: Serviço API

**User Story:** Como desenvolvedor, quero um serviço FastAPI isolado em contêiner, para que a camada de exposição de dados seja independente dos demais serviços.

#### Acceptance Criteria

1. THE API SHALL ser construída a partir de um Dockerfile localizado em `./api`.
2. THE API SHALL expor a porta 8000 do contêiner para a porta 8000 do host.
3. THE API SHALL receber a variável de ambiente `DATABASE_URL`.
4. WHEN a API é iniciada, THE API SHALL executar o servidor uvicorn apontando para `api.main:app`.
5. THE API SHALL utilizar a imagem base `python:3.11-slim` e instalar dependências a partir de `requirements.txt`.

---

### Requirement 5: Variáveis de Ambiente

**User Story:** Como desenvolvedor, quero um arquivo `.env.example` com todas as variáveis necessárias documentadas, para que novos colaboradores saibam quais valores configurar.

#### Acceptance Criteria

1. THE Astraea SHALL fornecer um arquivo `.env.example` contendo as variáveis: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL` e `NASA_API_KEY`.
2. THE Astraea SHALL utilizar valores de exemplo seguros e não funcionais em `.env.example` (ex.: `changeme`, `DEMO_KEY`).
3. IF o arquivo `.env` não existir, THEN THE Docker_Compose SHALL falhar com mensagem de variável ausente, sinalizando ao operador que o arquivo deve ser criado.

---

### Requirement 6: Inicialização do Banco de Dados

**User Story:** Como desenvolvedor, quero que os schemas e tabelas sejam criados automaticamente na primeira inicialização, para que o banco esteja pronto para uso sem intervenção manual.

#### Acceptance Criteria

1. WHEN o DB é inicializado pela primeira vez, THE Init_Script SHALL criar os schemas `raw`, `staging` e `mart`.
2. THE Init_Script SHALL criar a tabela `raw.neo_feeds` com as colunas: `id SERIAL PRIMARY KEY`, `neo_id VARCHAR(50) NOT NULL`, `name VARCHAR(200)`, `raw_data JSONB NOT NULL`, `ingested_at TIMESTAMPTZ DEFAULT NOW()`, `feed_date DATE NOT NULL`.
3. THE Init_Script SHALL criar a tabela `raw.solar_events` com as colunas: `id SERIAL PRIMARY KEY`, `event_id VARCHAR(100) NOT NULL`, `event_type VARCHAR(50) NOT NULL`, `raw_data JSONB NOT NULL`, `ingested_at TIMESTAMPTZ DEFAULT NOW()`, `event_date DATE NOT NULL`.
4. THE Init_Script SHALL criar índices em `raw.neo_feeds(neo_id)`, `raw.neo_feeds(feed_date)`, `raw.solar_events(event_type)` e `raw.solar_events(event_date)`.
5. THE Init_Script SHALL aplicar a constraint `UNIQUE(neo_id, feed_date)` na tabela `raw.neo_feeds`.
6. IF o Init_Script for executado em um banco já inicializado, THEN THE Init_Script SHALL ignorar objetos já existentes sem retornar erro (uso de `IF NOT EXISTS`).
7. THE Docker_Compose SHALL montar o arquivo `./scripts/init_db.sql` via bind mount no caminho `/docker-entrypoint-initdb.d/init_db.sql` do serviço db, aproveitando o comportamento nativo do PostgreSQL 15-alpine que executa automaticamente qualquer `.sql` nesse diretório na primeira inicialização. O script NÃO deve ser executado manualmente.

---

### Requirement 7: Controle de Versão

**User Story:** Como desenvolvedor, quero um `.gitignore` adequado ao projeto, para que arquivos sensíveis e artefatos de build não sejam commitados acidentalmente.

#### Acceptance Criteria

1. THE Astraea SHALL fornecer um arquivo `.gitignore` que exclua o arquivo `.env`.
2. THE Astraea SHALL fornecer um arquivo `.gitignore` que exclua diretórios e arquivos gerados: `__pycache__`, `*.pyc`, `.venv`, `venv`, `*.egg-info`, `dist`, `build`.
3. THE Astraea SHALL fornecer um arquivo `.gitignore` que exclua artefatos do dbt: `.dbt`, `target/`, `dbt_packages/`.
4. THE Astraea SHALL fornecer um arquivo `.gitignore` que exclua arquivos de log: `logs/`, `*.log`.
5. THE Astraea SHALL fornecer um arquivo `.gitignore` que exclua artefatos de sistema e notebooks: `.DS_Store`, `notebooks/.ipynb_checkpoints`, `ml/models/*.joblib`.

---

### Requirement 8: Estrutura de Diretórios

**User Story:** Como desenvolvedor, quero uma estrutura de pastas padronizada, para que cada componente da plataforma tenha um local definido desde o início.

#### Acceptance Criteria

1. THE Astraea SHALL conter os diretórios: `collector/`, `api/`, `dbt/`, `ml/`, `dashboard/`, `notebooks/`, `scripts/`.
2. THE Collector SHALL conter os arquivos `__init__.py` e `main.py` como placeholders do serviço de coleta.
3. THE API SHALL conter os arquivos `__init__.py` e `main.py` como placeholders do serviço de exposição de dados.
4. WHEN os diretórios `dbt/`, `ml/`, `dashboard/` e `notebooks/` não contiverem arquivos de implementação, THE Astraea SHALL manter um arquivo `.gitkeep` em cada um para preservar a estrutura no controle de versão.
