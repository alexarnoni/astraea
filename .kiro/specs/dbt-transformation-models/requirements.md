# Requirements Document

## Introduction

Esta feature configura o dbt (data build tool) no projeto Astraea e implementa os modelos de transformação de dados astronômicos. O objetivo é criar uma camada de transformação reproduzível e testável que extrai campos JSONB das tabelas raw, tipifica os dados nas camadas staging e enriquece com regras de negócio na camada mart — preparando os dados para consumo pela API e futuramente pelo modelo de ML.

O projeto usa dbt-postgres 1.8.2 com PostgreSQL 15 rodando em localhost:5432. Os dados de entrada são `raw.neo_feeds` (objetos próximos da Terra, NEOs) e `raw.solar_events` (eventos solares CME e GST).

## Glossary

- **dbt**: Data Build Tool — ferramenta de transformação SQL com versionamento, testes e documentação
- **Profile**: Arquivo `~/.dbt/profiles.yml` com credenciais de conexão ao banco de dados
- **Project**: Diretório `dbt/astraea/` com configuração `dbt_project.yml` e modelos SQL
- **Source**: Tabela raw declarada em `sources.yml` que serve como entrada para os modelos
- **Model**: Arquivo SQL que define uma transformação; materializado como view ou table
- **Staging_Model**: Modelo que extrai e tipifica campos JSONB das tabelas raw; materializado como view no schema `staging`
- **Mart_Model**: Modelo que enriquece dados de staging com regras de negócio; materializado como table no schema `mart`
- **NEO**: Near-Earth Object — asteroide ou cometa com órbita próxima à Terra
- **CME**: Coronal Mass Ejection — ejeção de massa coronal do Sol
- **GST**: Geomagnetic Storm — tempestade geomagnética causada por atividade solar
- **JSONB**: Tipo de dado PostgreSQL para armazenamento de JSON binário
- **risk_score**: Pontuação numérica de risco calculada por regras determinísticas (temporária, será substituída por ML na Task 04)
- **risk_label**: Classificação categórica de risco derivada do risk_score; exibida no frontend para usuários finais em português (`'alto'`, `'médio'`, `'baixo'`)
- **intensity_label**: Classificação categórica de intensidade de evento solar; exibida no frontend para usuários finais em português (`'extremo'`, `'moderado'`, `'fraco'`, `'severo'`, `'desconhecido'`)

---

## Requirements

### Requirement 1: Configurar Conexão dbt com PostgreSQL

**User Story:** Como engenheiro de dados, quero configurar o profile dbt com as credenciais do banco astraea, para que o dbt consiga se conectar ao PostgreSQL local.

#### Acceptance Criteria

1. THE Profile SHALL ser criado em `~/.dbt/profiles.yml` com o nome de profile `astraea`
2. THE Profile SHALL conter as credenciais: host `localhost`, port `5432`, database `astraea`, user `astraea`, password `changeme`, schema padrão `staging`
3. WHEN o comando `dbt debug` for executado no diretório do projeto, THE dbt SHALL retornar "All checks passed" sem erros de conexão
4. IF a conexão com o banco falhar, THEN THE dbt SHALL exibir uma mensagem de erro descritiva indicando o parâmetro de conexão inválido

---

### Requirement 2: Inicializar Projeto dbt

**User Story:** Como engenheiro de dados, quero inicializar a estrutura do projeto dbt dentro da pasta `dbt/`, para que os modelos e configurações fiquem organizados e versionados no repositório.

#### Acceptance Criteria

1. THE Project SHALL ser inicializado dentro de `dbt/astraea/` usando `dbt init astraea --skip-profile-setup`
2. THE Project SHALL conter o arquivo `dbt_project.yml` com `name: astraea` e `profile: astraea`
3. THE dbt_project.yml SHALL configurar o modelo `staging` com `+materialized: view` e schema `staging`
4. THE dbt_project.yml SHALL configurar o modelo `mart` com `+materialized: table` e schema `mart`
5. THE Project SHALL remover os modelos de exemplo gerados pelo `dbt init` (pasta `models/example/`)

---

### Requirement 3: Declarar Sources com Testes de Qualidade

**User Story:** Como engenheiro de dados, quero declarar as tabelas raw como sources dbt com testes automáticos, para que a integridade dos dados de entrada seja verificada a cada execução.

#### Acceptance Criteria

1. THE sources.yml SHALL declarar `raw.neo_feeds` como source com os campos `id`, `neo_id`, `name`, `raw_data`, `feed_date`, `ingested_at`
2. THE sources.yml SHALL declarar `raw.solar_events` como source com os campos `id`, `event_id`, `event_type`, `raw_data`, `event_date`, `ingested_at`
3. THE sources.yml SHALL aplicar teste `not_null` nos campos `neo_id` e `feed_date` de `raw.neo_feeds`
4. THE sources.yml SHALL aplicar teste `unique` no campo `neo_id` combinado com `feed_date` de `raw.neo_feeds` (via `dbt_utils` ou teste customizado)
5. THE sources.yml SHALL aplicar teste `not_null` nos campos `event_id` e `event_type` de `raw.solar_events`
6. WHEN `dbt test --select source:astraea` for executado, THE dbt SHALL passar todos os testes de source sem falhas

---

### Requirement 4: Criar Modelo Staging de Asteroides

**User Story:** Como engenheiro de dados, quero um modelo staging que extraia e tipifique os campos JSONB de `raw.neo_feeds`, para que os dados de asteroides fiquem estruturados e prontos para análise.

#### Acceptance Criteria

1. THE Staging_Model `stg_asteroids` SHALL extrair do campo `raw_data` JSONB os seguintes campos tipificados:
   - `neo_id` (text) — identificador único do NEO
   - `name` (text) — nome do NEO
   - `feed_date` (date) — data do feed
   - `absolute_magnitude_h` (float) — magnitude absoluta
   - `is_potentially_hazardous` (boolean) — flag de perigo potencial
   - `estimated_diameter_min_km` (float) — diâmetro mínimo estimado em km
   - `estimated_diameter_max_km` (float) — diâmetro máximo estimado em km
   - `close_approach_date` (date) — data da aproximação mais próxima
   - `relative_velocity_km_s` (float) — velocidade relativa em km/s
   - `miss_distance_km` (float) — distância de miss em km
2. THE Staging_Model SHALL ser materializado como view no schema `staging`
3. WHEN `dbt run --select stg_asteroids` for executado, THE dbt SHALL criar a view `staging.stg_asteroids` sem erros
4. THE Staging_Model SHALL retornar o mesmo número de linhas que `raw.neo_feeds` (invariante de contagem)
5. IF um campo JSONB esperado estiver ausente no registro, THEN THE Staging_Model SHALL retornar NULL para esse campo sem falhar

---

### Requirement 5: Criar Modelo Staging de Eventos Solares

**User Story:** Como engenheiro de dados, quero um modelo staging que extraia os campos JSONB de `raw.solar_events` para CME e GST, para que os eventos solares fiquem estruturados por tipo.

#### Acceptance Criteria

1. THE Staging_Model `stg_solar_events` SHALL extrair do campo `raw_data` JSONB os seguintes campos:
   - `event_id` (text) — identificador único do evento
   - `event_type` (text) — tipo do evento: `CME` ou `GST`
   - `event_date` (date) — data do evento
   - `start_time` (timestamp) — horário de início do evento
   - Para CME: `cme_type` (text), `speed_km_s` (float), `half_angle_deg` (float), `latitude` (float), `longitude` (float), `note` (text)
   - Para GST: `kp_index_max` (float) — índice Kp máximo da tempestade
2. THE Staging_Model SHALL ser materializado como view no schema `staging`
3. WHEN `dbt run --select stg_solar_events` for executado, THE dbt SHALL criar a view `staging.stg_solar_events` sem erros
4. THE Staging_Model SHALL retornar o mesmo número de linhas que `raw.solar_events` (invariante de contagem)
5. IF um campo não existir para um tipo de evento (ex: `speed_km_s` para GST), THEN THE Staging_Model SHALL retornar NULL para esse campo

---

### Requirement 6: Criar Modelo Mart de Asteroides com Regras de Risco

**User Story:** Como analista de dados, quero um modelo mart que enriqueça os asteroides com pontuação e classificação de risco baseadas em regras, para que seja possível identificar NEOs de alta prioridade antes da implementação do modelo de ML.

#### Acceptance Criteria

1. THE Mart_Model `mart_asteroids` SHALL selecionar todos os campos de `stg_asteroids`
2. THE Mart_Model SHALL calcular `risk_score` como pontuação numérica baseada nas seguintes regras determinísticas:
   - `is_potentially_hazardous = true`: +3 pontos
   - `relative_velocity_km_s > 20`: +2 pontos
   - `miss_distance_km < 1000000`: +2 pontos
   - `estimated_diameter_max_km > 0.5`: +1 ponto
3. THE Mart_Model SHALL calcular `risk_label` baseado no `risk_score`:
   - `risk_score >= 6`: `'alto'`
   - `risk_score >= 3`: `'médio'`
   - `risk_score < 3`: `'baixo'`
4. THE Mart_Model SHALL ser materializado como table no schema `mart`
5. WHEN `dbt run --select mart_asteroids` for executado, THE dbt SHALL criar a tabela `mart.mart_asteroids` sem erros
6. THE Mart_Model SHALL retornar o mesmo número de linhas que `stg_asteroids` (invariante de contagem)
7. THE `risk_score` SHALL ser um valor inteiro entre 0 e 8 para qualquer registro válido

---

### Requirement 7: Criar Modelo Mart de Eventos Solares com Classificação de Intensidade

**User Story:** Como analista de dados, quero um modelo mart que enriqueça os eventos solares com classificação de intensidade, para que seja possível priorizar alertas por severidade.

#### Acceptance Criteria

1. THE Mart_Model `mart_solar_events` SHALL selecionar todos os campos de `stg_solar_events`
2. THE Mart_Model SHALL calcular `intensity_label` baseado nas seguintes regras:
   - Para CME: baseado em `speed_km_s`: `>= 1000` → `'extremo'`, `>= 500` → `'moderado'`, `>= 200` → `'fraco'`, `< 200` → `'fraco'`
   - Para GST: baseado em `kp_index_max`: `>= 8` → `'extremo'`, `>= 7` → `'severo'`, `>= 5` → `'moderado'`, `< 5` → `'fraco'`
   - IF `event_type` não for CME nem GST, THEN `intensity_label` SHALL ser `'desconhecido'`
3. THE Mart_Model SHALL ser materializado como table no schema `mart`
4. WHEN `dbt run --select mart_solar_events` for executado, THE dbt SHALL criar a tabela `mart.mart_solar_events` sem erros
5. THE Mart_Model SHALL retornar o mesmo número de linhas que `stg_solar_events` (invariante de contagem)
6. THE `intensity_label` SHALL ser um dos valores: `'extremo'`, `'severo'`, `'moderado'`, `'fraco'`, `'desconhecido'`

---

### Requirement 8: Validar Pipeline Completo com Testes dbt

**User Story:** Como engenheiro de dados, quero executar o pipeline completo de testes dbt, para que a qualidade e integridade de todos os modelos sejam verificadas automaticamente.

#### Acceptance Criteria

1. WHEN `dbt run` for executado, THE dbt SHALL criar os 4 modelos (`stg_asteroids`, `stg_solar_events`, `mart_asteroids`, `mart_solar_events`) sem erros
2. WHEN `dbt test` for executado, THE dbt SHALL passar todos os testes sem falhas
3. THE staging.stg_asteroids SHALL conter exatamente o mesmo número de linhas que `raw.neo_feeds`
4. THE staging.stg_solar_events SHALL conter exatamente o mesmo número de linhas que `raw.solar_events`
5. THE mart.mart_asteroids SHALL conter exatamente o mesmo número de linhas que `staging.stg_asteroids`
6. THE mart.mart_solar_events SHALL conter exatamente o mesmo número de linhas que `staging.stg_solar_events`
7. THE `risk_label` em `mart_asteroids` SHALL conter apenas os valores `'alto'`, `'médio'`, `'baixo'`
8. THE `intensity_label` em `mart_solar_events` SHALL conter apenas os valores `'extremo'`, `'severo'`, `'moderado'`, `'fraco'`, `'desconhecido'`
