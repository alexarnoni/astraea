# Requirements Document

## Introduction

Esta feature extrai quatro novos campos do `raw_data` dos asteroides armazenados no banco de dados e os propaga por toda a stack: camada de staging dbt → mart dbt → API FastAPI → dashboard de detalhe. Os campos são `orbit_class` (grupo orbital), `is_sentry_object` (presença na lista Sentry da NASA), `first_observation_date` (data da primeira observação) e `nasa_jpl_url` (link direto para o JPL Small-Body Database).

## Glossary

- **Staging_Model**: modelo dbt `stg_asteroids.sql` que lê de `neo_feeds` e normaliza os campos do `raw_data`.
- **Mart_Model**: modelo dbt `mart_asteroids.sql` que consome o Staging_Model e aplica scoring de risco.
- **API**: serviço FastAPI que expõe os dados do mart via endpoints REST.
- **AsteroidResponse**: schema Pydantic que define os campos retornados pelo endpoint de asteroides.
- **Row_Mapper**: função `_row_to_asteroid` em `api/routers/asteroids.py` que converte uma linha do banco em `AsteroidResponse`.
- **Dashboard**: aplicação frontend em JavaScript que consome a API e renderiza a página de detalhe do asteroide.
- **Sentry_List**: lista mantida pela NASA com objetos de risco não-zero de impacto com a Terra nos próximos 100 anos.
- **Orbit_Class**: classificação do grupo orbital do asteroide (ex.: Apollo, Aten, Amor).
- **JPL_URL**: URL direta para o registro do asteroide no NASA JPL Small-Body Database.

## Requirements

### Requirement 1: Extração dos novos campos no Staging Model

**User Story:** Como engenheiro de dados, quero extrair `orbit_class`, `is_sentry_object`, `first_observation_date` e `nasa_jpl_url` do `raw_data`, para que esses campos estejam disponíveis nas camadas downstream.

#### Acceptance Criteria

1. THE Staging_Model SHALL selecionar `raw_data -> 'orbital_data' ->> 'orbit_class_type'` como `orbit_class`.
2. THE Staging_Model SHALL selecionar `(raw_data ->> 'is_sentry_object')::boolean` como `is_sentry_object`.
3. THE Staging_Model SHALL selecionar `raw_data -> 'orbital_data' ->> 'first_observation_date'` como `first_observation_date`.
4. THE Staging_Model SHALL selecionar `raw_data ->> 'nasa_jpl_url'` como `nasa_jpl_url`.
5. WHEN o campo `is_sentry_object` estiver ausente no `raw_data`, THE Staging_Model SHALL retornar `NULL` para `is_sentry_object`.
6. WHEN o campo `orbit_class_type` estiver ausente no `raw_data`, THE Staging_Model SHALL retornar `NULL` para `orbit_class`.

---

### Requirement 2: Propagação dos campos no Mart Model

**User Story:** Como engenheiro de dados, quero que os quatro novos campos sejam propagados para o mart, para que a API e o dashboard possam consumi-los.

#### Acceptance Criteria

1. THE Mart_Model SHALL incluir `orbit_class`, `is_sentry_object`, `first_observation_date` e `nasa_jpl_url` no resultado final do `SELECT`.
2. THE Mart_Model SHALL preservar os valores originais dos quatro campos sem transformação adicional.
3. WHEN o Staging_Model retornar `NULL` para qualquer dos quatro campos, THE Mart_Model SHALL propagar `NULL` para o campo correspondente.

---

### Requirement 3: Exposição dos campos na API

**User Story:** Como desenvolvedor de frontend, quero que a API retorne os quatro novos campos no payload do asteroide, para que o dashboard possa exibi-los.

#### Acceptance Criteria

1. THE AsteroidResponse SHALL declarar `orbit_class: Optional[str] = None`.
2. THE AsteroidResponse SHALL declarar `is_sentry_object: Optional[bool] = None`.
3. THE AsteroidResponse SHALL declarar `first_observation_date: Optional[str] = None`.
4. THE AsteroidResponse SHALL declarar `nasa_jpl_url: Optional[str] = None`.
5. THE Row_Mapper SHALL mapear `row.orbit_class` para o campo `orbit_class` do `AsteroidResponse`.
6. THE Row_Mapper SHALL mapear `row.is_sentry_object` para o campo `is_sentry_object` do `AsteroidResponse`.
7. THE Row_Mapper SHALL mapear `row.first_observation_date` para o campo `first_observation_date` do `AsteroidResponse`.
8. THE Row_Mapper SHALL mapear `row.nasa_jpl_url` para o campo `nasa_jpl_url` do `AsteroidResponse`.
9. WHEN `orbit_class`, `is_sentry_object`, `first_observation_date` ou `nasa_jpl_url` forem `NULL` no banco, THE Row_Mapper SHALL retornar `None` para o campo correspondente.

---

### Requirement 4: Exibição do badge Sentry no hero do dashboard

**User Story:** Como usuário do dashboard, quero ver um badge de alerta quando o asteroide está na lista Sentry, para que eu entenda que ele representa risco real de impacto.

#### Acceptance Criteria

1. WHEN `is_sentry_object` for `true`, THE Dashboard SHALL renderizar um badge com o texto "// LISTA SENTRY" na seção hero do asteroide.
2. WHEN `is_sentry_object` for `true`, THE Dashboard SHALL aplicar estilo vermelho pulsante ao badge Sentry.
3. WHEN `is_sentry_object` for `false` ou `null`, THE Dashboard SHALL omitir o badge Sentry do hero.
4. THE Dashboard SHALL exibir no badge Sentry o tooltip: "Este objeto está na lista Sentry da NASA — tem probabilidade não-zero de impacto com a Terra nos próximos 100 anos".

---

### Requirement 5: Exibição do grupo orbital nos metric cards

**User Story:** Como usuário do dashboard, quero ver o grupo orbital do asteroide nos metric cards, para que eu entenda a família orbital à qual ele pertence.

#### Acceptance Criteria

1. THE Dashboard SHALL renderizar um metric card com label "Grupo orbital" exibindo o valor de `orbit_class`.
2. WHEN `orbit_class` for `null`, THE Dashboard SHALL exibir "—" no metric card de grupo orbital.
3. THE Dashboard SHALL exibir no metric card de grupo orbital um tooltip explicando os grupos Apollo, Aten e Amor.

---

### Requirement 6: Exibição da data de primeira observação nos metric cards

**User Story:** Como usuário do dashboard, quero ver a data da primeira observação do asteroide, para que eu saiba há quanto tempo ele é monitorado.

#### Acceptance Criteria

1. THE Dashboard SHALL renderizar um metric card com label "Descoberto em" exibindo `first_observation_date` formatado em português (pt-BR).
2. WHEN `first_observation_date` for `null`, THE Dashboard SHALL exibir "—" no metric card de descoberta.

---

### Requirement 7: Link JPL dinâmico no dashboard

**User Story:** Como usuário do dashboard, quero que o link para o NASA JPL use a URL real retornada pela API, para que o link seja sempre preciso e atualizado.

#### Acceptance Criteria

1. WHEN `nasa_jpl_url` estiver disponível na resposta da API, THE Dashboard SHALL usar `nasa_jpl_url` como `href` do link JPL.
2. WHEN `nasa_jpl_url` for `null`, THE Dashboard SHALL usar a URL construída com o `neo_id` como fallback: `https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr={neo_id}`.
3. THE Dashboard SHALL manter o atributo `target="_blank" rel="noopener"` no link JPL independentemente da origem da URL.
