# Implementation Plan: asteroid-new-fields

## Overview

Propaga quatro novos campos (`orbit_class`, `is_sentry_object`, `first_observation_date`, `nasa_jpl_url`) do `raw_data` JSONB por toda a stack: staging dbt → mart dbt → API FastAPI → dashboard de detalhe.

## Tasks

- [x] 1. Adicionar os quatro novos campos ao staging model dbt
  - Editar `dbt/astraea/models/staging/stg_asteroids.sql` adicionando as quatro expressões SQL ao bloco `renamed`
  - Extrair `raw_data -> 'orbital_data' ->> 'orbit_class_type'` como `orbit_class`
  - Extrair `(raw_data ->> 'is_sentry_object')::boolean` como `is_sentry_object`
  - Extrair `raw_data -> 'orbital_data' ->> 'first_observation_date'` como `first_observation_date`
  - Extrair `raw_data ->> 'nasa_jpl_url'` como `nasa_jpl_url`
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 2. Verificar pass-through no mart model dbt
  - Confirmar que `dbt/astraea/models/mart/mart_asteroids.sql` já usa `select *` e propaga os campos automaticamente
  - Adicionar teste SQL `dbt/astraea/tests/assert_new_fields_present.sql` que verifica que as quatro colunas existem e não são todas NULL
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 3. Adicionar os quatro campos ao schema Pydantic `AsteroidResponse`
  - Editar `api/models.py` adicionando `orbit_class: Optional[str] = None`, `is_sentry_object: Optional[bool] = None`, `first_observation_date: Optional[str] = None`, `nasa_jpl_url: Optional[str] = None`
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 4. Mapear os quatro campos no Row_Mapper da API
  - [x] 4.1 Editar `_row_to_asteroid()` em `api/routers/asteroids.py` adicionando os quatro mapeamentos
    - Mapear `row.orbit_class`, `row.is_sentry_object`, `row.nasa_jpl_url` diretamente
    - Mapear `first_observation_date` com `str(row.first_observation_date) if row.first_observation_date is not None else None`
    - _Requirements: 3.5, 3.6, 3.7, 3.8, 3.9_

  - [x]* 4.2 Escrever property test para o Row_Mapper (Property 3)
    - Criar `api/tests/test_asteroids_router.py` com teste hypothesis
    - **Property 3: Round-trip do Row_Mapper**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9**

- [x] 5. Checkpoint — Garantir que a API retorna os novos campos
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implementar badge Sentry no `renderHero()` do dashboard
  - [x] 6.1 Editar `renderHero()` em `dashboard/js/detalhe.js` adicionando `sentryBadge` condicional após `hazardousBadge`
    - Renderizar `<div class="hero__sentry-badge hero__sentry-badge--pulse">// LISTA SENTRY</div>` quando `is_sentry_object` for `true`
    - Incluir tooltip com o texto sobre a lista Sentry da NASA
    - Omitir o badge quando `is_sentry_object` for `false` ou `null`
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x]* 6.2 Escrever property tests para badge Sentry (Properties 4 e 5)
    - Criar `dashboard/tests/detalhe.test.js`
    - **Property 4: Badge Sentry presente quando is_sentry_object é true**
    - **Property 5: Badge Sentry ausente quando is_sentry_object é false ou null**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**

- [x] 7. Adicionar estilo CSS para o badge Sentry
  - Editar `dashboard/css/style.css` adicionando classes `.hero__sentry-badge` e `.hero__sentry-badge--pulse`
  - Aplicar cor vermelha e animação `pulse` ao badge
  - _Requirements: 4.2_

- [x] 8. Adicionar metric cards de `orbit_class` e `first_observation_date`
  - [x] 8.1 Editar `renderMetricCards()` em `dashboard/js/detalhe.js` adicionando dois novos cards ao array `cards`
    - Card "Grupo orbital": valor `asteroid.orbit_class ?? "—"`, tooltip mencionando Apollo, Aten e Amor
    - Card "Descoberto em": valor `formatDate(asteroid.first_observation_date)`, tooltip sobre primeira observação
    - _Requirements: 5.1, 5.2, 5.3, 6.1, 6.2_

  - [x]* 8.2 Escrever property tests para metric cards (Properties 6 e 7)
    - Adicionar testes em `dashboard/tests/detalhe.test.js`
    - **Property 6: Metric card orbit_class renderiza valor e tooltip**
    - **Property 7: Metric card first_observation_date renderiza data formatada**
    - **Validates: Requirements 5.1, 5.2, 5.3, 6.1, 6.2**

- [x] 9. Atualizar `renderJPLLink()` para usar `nasa_jpl_url` dinâmico
  - [x] 9.1 Alterar assinatura de `renderJPLLink(id)` para `renderJPLLink(id, url)` em `dashboard/js/detalhe.js`
    - Usar `url ?? \`https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=${id}\`` como `href`
    - Manter `target="_blank" rel="noopener"` em ambos os casos
    - Atualizar a chamada no bootstrap para `renderJPLLink(neoId, asteroid.nasa_jpl_url)`
    - _Requirements: 7.1, 7.2, 7.3_

  - [x]* 9.2 Escrever property test para link JPL (Property 8)
    - Adicionar teste em `dashboard/tests/detalhe.test.js`
    - **Property 8: Link JPL usa nasa_jpl_url quando disponível, fallback quando null**
    - **Validates: Requirements 7.1, 7.2, 7.3**

- [x] 10. Checkpoint final — Garantir que todos os testes passam
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marcadas com `*` são opcionais e podem ser puladas para MVP mais rápido
- O mart model não precisa de alteração de código pois já usa `select *` do staging
- `first_observation_date` é tratado como `str` em toda a stack para evitar problemas de formato
- Property tests JS usam fast-check (já instalado); property tests Python usam hypothesis
