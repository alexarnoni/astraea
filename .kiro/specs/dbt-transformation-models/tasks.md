# Implementation Plan: dbt Transformation Models

## Overview

Implementação incremental da pipeline dbt para o projeto Astraea: configuração do ambiente, inicialização do projeto, declaração de sources, modelos staging, modelos mart e testes de qualidade.

## Tasks

- [x] 1. Configurar ambiente dbt e conexão com PostgreSQL
  - Criar o arquivo `~/.dbt/profiles.yml` com o profile `astraea` apontando para `localhost:5432`, banco `astraea`, schema padrão `staging`
  - Instalar `dbt-postgres==1.8.2` no venv `.venv-dbt` (verificar se já instalado)
  - _Requirements: 1.1, 1.2_

- [x] 2. Inicializar projeto dbt em `dbt/astraea/`
  - [x] 2.1 Executar `dbt init astraea --skip-profile-setup` dentro de `dbt/` e remover a pasta `models/example/` gerada
    - _Requirements: 2.1, 2.5_
  - [x] 2.2 Configurar `dbt_project.yml` com `name: astraea`, `profile: astraea`, materialização `view` para staging e `table` para mart com schemas corretos
    - _Requirements: 2.2, 2.3, 2.4_

- [x] 3. Declarar sources com testes de qualidade
  - [x] 3.1 Criar `models/staging/sources.yml` declarando `raw.neo_feeds` e `raw.solar_events` com todos os campos listados no design
    - _Requirements: 3.1, 3.2_
  - [x] 3.2 Adicionar testes `not_null` em `neo_id` e `feed_date` de `neo_feeds`, e `not_null` em `event_id` e `event_type` de `solar_events`
    - _Requirements: 3.3, 3.5_
  - [ ]* 3.3 Adicionar teste de unicidade combinada `(neo_id, feed_date)` em `neo_feeds` via teste customizado SQL em `tests/`
    - _Requirements: 3.4_

- [x] 4. Implementar modelo staging de asteroides
  - [x] 4.1 Criar `models/staging/stg_asteroids.sql` extraindo os 10 campos JSONB tipificados conforme o design (operadores `->>`/`->` do PostgreSQL)
    - _Requirements: 4.1, 4.2, 4.5_
  - [ ]* 4.2 Escrever property test para extração JSONB de asteroides
    - **Property 3: Extração JSONB de asteroides preserva dados**
    - **Validates: Requirements 4.1, 4.5**
    - Usar Hypothesis para gerar dicts JSONB com campos presentes/ausentes e verificar tipos e NULLs
    - Arquivo: `tests/test_properties.py`

- [x] 5. Implementar modelo staging de eventos solares
  - [x] 5.1 Criar `models/staging/stg_solar_events.sql` extraindo campos comuns (CME+GST) e campos específicos por tipo com CASE WHEN, retornando NULL para campos do outro tipo
    - _Requirements: 5.1, 5.2, 5.5_
  - [ ]* 5.2 Escrever property test para extração JSONB de eventos solares por tipo
    - **Property 4: Extração JSONB de eventos solares por tipo**
    - **Validates: Requirements 5.1, 5.5**
    - Gerar eventos CME e GST aleatórios, verificar campos corretos e NULLs cruzados

- [x] 6. Checkpoint — Verificar modelos staging
  - Garantir que `dbt run --select staging` cria as views `staging.stg_asteroids` e `staging.stg_solar_events` sem erros. Perguntar ao usuário se houver dúvidas.

- [x] 7. Implementar modelo mart de asteroides
  - [x] 7.1 Criar `models/mart/mart_asteroids.sql` selecionando todos os campos de `stg_asteroids` e calculando `risk_score` (soma de CASE WHEN) e `risk_label` conforme as regras do design
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
  - [ ]* 7.2 Escrever property test para cálculo determinístico do risk_score
    - **Property 5: Cálculo determinístico do risk_score**
    - **Validates: Requirements 6.2**
    - Gerar combinações de `is_potentially_hazardous`, `relative_velocity_km_s`, `miss_distance_km`, `estimated_diameter_max_km` e verificar soma exata
  - [ ]* 7.3 Escrever property test para invariante de domínio do risk_score
    - **Property 6: Invariante de domínio do risk_score**
    - **Validates: Requirements 6.7, 8.7**
    - Verificar que `0 <= risk_score <= 8` para qualquer entrada válida
  - [ ]* 7.4 Escrever property test para mapeamento correto do risk_label
    - **Property 7: Mapeamento correto do risk_label**
    - **Validates: Requirements 6.3, 8.7**
    - Verificar que o label é exatamente `'alto'`/`'médio'`/`'baixo'` conforme os limiares e que o conjunto de valores é fechado

- [x] 8. Implementar modelo mart de eventos solares
  - [x] 8.1 Criar `models/mart/mart_solar_events.sql` selecionando todos os campos de `stg_solar_events` e calculando `intensity_label` com CASE WHEN aninhado por `event_type`
    - _Requirements: 7.1, 7.2, 7.3_
  - [ ]* 8.2 Escrever property test para cálculo correto do intensity_label
    - **Property 8: Cálculo correto do intensity_label**
    - **Validates: Requirements 7.2**
    - Gerar eventos CME com speeds aleatórios e GST com kp_index aleatórios, verificar label correto por limiares
  - [ ]* 8.3 Escrever property test para invariante de domínio do intensity_label
    - **Property 9: Invariante de domínio do intensity_label**
    - **Validates: Requirements 7.6, 8.8**
    - Verificar que o label está sempre no conjunto `{'extremo', 'severo', 'moderado', 'fraco', 'desconhecido'}`

- [x] 9. Checkpoint — Verificar modelos mart
  - Garantir que `dbt run --select mart` cria as tabelas `mart.mart_asteroids` e `mart.mart_solar_events` sem erros. Perguntar ao usuário se houver dúvidas.

- [x] 10. Criar testes dbt customizados para invariantes de contagem e domínio
  - [x] 10.1 Criar `tests/assert_asteroids_count_preserved.sql` verificando que `mart_asteroids` tem o mesmo número de linhas que `raw.neo_feeds`
    - _Requirements: 4.4, 6.6, 8.3, 8.5_
  - [x] 10.2 Criar `tests/assert_solar_events_count_preserved.sql` verificando que `mart_solar_events` tem o mesmo número de linhas que `raw.solar_events`
    - _Requirements: 5.4, 7.5, 8.4, 8.6_
  - [x] 10.3 Criar `tests/assert_risk_score_range.sql` verificando que `risk_score` está no intervalo [0, 8]
    - _Requirements: 6.7_
  - [x] 10.4 Criar `tests/assert_risk_label_values.sql` verificando que `risk_label` contém apenas `'alto'`, `'médio'`, `'baixo'`
    - _Requirements: 8.7_
  - [x] 10.5 Criar `tests/assert_intensity_label_values.sql` verificando que `intensity_label` contém apenas os 5 valores permitidos
    - _Requirements: 8.8_
  - [ ]* 10.6 Escrever property tests para invariantes de contagem (asteroides e solar)
    - **Property 1: Invariante de contagem — pipeline de asteroides**
    - **Property 2: Invariante de contagem — pipeline de eventos solares**
    - **Validates: Requirements 4.4, 5.4, 6.6, 7.5, 8.3, 8.4, 8.5, 8.6**
    - Gerar listas de registros e verificar que `len(staging) == len(raw) == len(mart)`

- [x] 11. Checkpoint final — Pipeline completa
  - Garantir que `dbt run` e `dbt test` passam sem erros para todos os 4 modelos. Perguntar ao usuário se houver dúvidas.

## Notes

- Tasks marcadas com `*` são opcionais e podem ser puladas para um MVP mais rápido
- Property tests usam Hypothesis (Python) no arquivo `tests/test_properties.py`
- Testes dbt customizados ficam em `dbt/astraea/tests/`
- Cada task referencia os requisitos específicos para rastreabilidade
- A lógica de `risk_score` é temporária e será substituída por ML na Task 04 do roadmap do projeto
