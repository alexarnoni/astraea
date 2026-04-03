# Implementation Plan: Astraea Base Infrastructure

## Overview

Criação de todos os arquivos de infraestrutura base da plataforma Astraea: orquestração Docker Compose, Dockerfiles, script SQL de inicialização, placeholders dos serviços, variáveis de ambiente e controle de versão.

## Tasks

- [x] 1. Criar estrutura de diretórios do projeto
  - Criar os diretórios: `collector/`, `api/`, `dbt/`, `ml/`, `dashboard/`, `notebooks/`, `scripts/`
  - Adicionar `.gitkeep` em `dbt/`, `ml/`, `dashboard/`, `notebooks/`
  - _Requirements: 8.1, 8.4_

- [x] 2. Criar script de inicialização do banco de dados
  - [x] 2.1 Implementar `scripts/init_db.sql`
    - Criar schemas `raw`, `staging`, `mart` com `IF NOT EXISTS`
    - Criar tabelas `raw.neo_feeds` e `raw.solar_events` com todas as colunas especificadas
    - Criar índices e constraint `UNIQUE(neo_id, feed_date)`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [ ]* 2.2 Escrever property test para idempotência do init_db.sql
    - **Property 1: Idempotência do script de inicialização**
    - **Validates: Requirements 6.6**

- [x] 3. Criar serviço Collector
  - [x] 3.1 Implementar `collector/main.py` placeholder
    - Loop infinito com `while True: time.sleep(3600)`
    - _Requirements: 3.3, 3.5_

  - [x] 3.2 Criar `collector/Dockerfile`
    - Imagem base `python:3.11-slim`, instalar dependências, CMD `python main.py`
    - _Requirements: 3.1, 3.4_

  - [x] 3.3 Criar `collector/requirements.txt`
    - Dependências mínimas do serviço collector
    - _Requirements: 3.4_

  - [x] 3.4 Criar `collector/__init__.py`
    - Arquivo placeholder vazio
    - _Requirements: 8.2_

- [x] 4. Criar serviço API
  - [x] 4.1 Implementar `api/main.py` placeholder
    - App FastAPI mínima com rota de health check
    - _Requirements: 4.4_

  - [x] 4.2 Criar `api/Dockerfile`
    - Imagem base `python:3.11-slim`, CMD com `uvicorn api.main:app`
    - _Requirements: 4.1, 4.5_

  - [x] 4.3 Criar `api/requirements.txt`
    - Dependências mínimas: `fastapi`, `uvicorn`
    - _Requirements: 4.5_

  - [x] 4.4 Criar `api/__init__.py`
    - Arquivo placeholder vazio
    - _Requirements: 8.3_

- [x] 5. Criar docker-compose.yml
  - Definir serviços `db`, `collector`, `api` com dependências, healthcheck, volumes e portas
  - Bind mount de `./scripts/init_db.sql` em `/docker-entrypoint-initdb.d/init_db.sql`
  - Volume nomeado `astraea_pgdata`, restart policy `unless-stopped`
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 2.2, 2.3, 2.4, 6.7_

- [x] 6. Criar arquivos de ambiente e controle de versão
  - [x] 6.1 Criar `.env.example`
    - Variáveis: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`, `NASA_API_KEY` com valores placeholder
    - _Requirements: 5.1, 5.2_

  - [x] 6.2 Criar `.gitignore`
    - Excluir `.env`, artefatos Python, dbt, logs, arquivos de sistema e notebooks
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 7. Checkpoint final — verificar consistência dos artefatos
  - Garantir que todos os arquivos existem e estão corretos, perguntar ao usuário se houver dúvidas.

## Notes

- Tasks marcadas com `*` são opcionais e podem ser puladas para MVP mais rápido
- Cada task referencia requisitos específicos para rastreabilidade
- O bind mount do `init_db.sql` é obrigatório — o script NÃO deve ser executado manualmente
- O `collector/main.py` DEVE conter o loop infinito com `time.sleep(3600)` como placeholder
