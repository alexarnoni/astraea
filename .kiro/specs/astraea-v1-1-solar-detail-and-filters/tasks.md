si# Plano de Implementação: Astraea v1.1 — Detalhe de Evento Solar e Filtros

## Visão Geral

Implementação incremental das três funcionalidades da v1.1: (1) endpoint de detalhe de evento solar na API, (2) página de detalhe de evento solar no frontend, e (3) filtro por data na página de asteroides. Cada tarefa segue os padrões existentes do projeto.

## Tarefas

- [x] 1. Backend — Modelo e mapper de eventos solares
  - [x] 1.1 Adicionar campo `is_earth_directed` ao `SolarEventResponse` em `api/models.py`
    - Adicionar `is_earth_directed: Optional[bool] = None` ao modelo Pydantic
    - _Requisitos: 1.4_
  - [x] 1.2 Atualizar `_row_to_solar` em `api/routers/solar_events.py` para mapear `is_earth_directed`
    - Adicionar `is_earth_directed=row.is_earth_directed` ao construtor do `SolarEventResponse`
    - _Requisitos: 1.4_
  - [ ]* 1.3 Escrever teste de propriedade para round-trip do `_row_to_solar`
    - **Propriedade 1: Round-trip do Row Mapper de eventos solares**
    - Criar `api/tests/test_solar_events_router.py` seguindo o padrão de `test_asteroids_router.py`
    - Gerar rows aleatórios com `SimpleNamespace` e `hypothesis`, verificar que todos os campos (incluindo `is_earth_directed`) são preservados após o mapper
    - Mínimo 100 iterações
    - **Valida: Requisitos 1.1, 1.4**

- [x] 2. Backend — Endpoint de detalhe de evento solar
  - [x] 2.1 Criar endpoint `GET /v1/solar-events/{event_id}` em `api/routers/solar_events.py`
    - Seguir o padrão de `GET /v1/asteroids/{neo_id}` em `asteroids.py`
    - Query parametrizada: `SELECT * FROM mart.mart_solar_events WHERE event_id = :event_id`
    - Retornar 404 com `{"detail": "Solar event not found"}` quando não encontrado
    - Aplicar rate limiter `60/minute`
    - Importar `HTTPException` do FastAPI
    - _Requisitos: 1.1, 1.2, 1.3, 1.5_
  - [ ]* 2.2 Escrever testes unitários para o endpoint de detalhe
    - Testar retorno 404 para `event_id` inexistente
    - _Requisitos: 1.2_

- [x] 3. Checkpoint — Verificar backend
  - Garantir que todos os testes passam, perguntar ao usuário se houver dúvidas.

- [x] 4. Frontend — Função `fetchSolarEvent` e suporte a filtros de data em `api.js`
  - [x] 4.1 Adicionar função `fetchSolarEvent(eventId)` em `dashboard/js/api.js`
    - Exportar função que chama `apiFetch(\`/v1/solar-events/${eventId}\`)`
    - Seguir o padrão de `fetchAsteroid(neo_id)`
    - _Requisitos: 3.1, 3.2_
  - [x] 4.2 Adicionar suporte a `start_date` e `end_date` em `fetchAsteroids` em `dashboard/js/api.js`
    - Desestruturar `start_date` e `end_date` dos parâmetros
    - Adicionar ao `URLSearchParams` quando não-nulos
    - _Requisitos: 5.2, 5.5_
  - [ ]* 4.3 Escrever teste de propriedade para URL do `fetchSolarEvent`
    - **Propriedade 6: Construção de URL do fetchSolarEvent**
    - Adicionar em `dashboard/tests/api.test.js`
    - Gerar `eventId` aleatórios, verificar que a URL construída é `/v1/solar-events/${eventId}`
    - Mínimo 100 iterações com `fast-check`
    - **Valida: Requisitos 3.2**
  - [ ]* 4.4 Escrever teste de propriedade para query string com filtros de data
    - **Propriedade 8: Construção de query string com filtros de data**
    - Adicionar em `dashboard/tests/api.test.js`
    - Gerar combinações de `start_date` e `end_date` (data válida ou `null`), verificar inclusão/omissão na query string
    - Mínimo 100 iterações com `fast-check`
    - **Valida: Requisitos 5.2, 5.4, 5.5**

- [x] 5. Frontend — Página de detalhe de evento solar
  - [x] 5.1 Criar `dashboard/detalhe-evento.html`
    - Seguir o padrão de `detalhe.html`: nav, breadcrumb, footer, bottom nav mobile
    - Breadcrumb: `Visão geral › Eventos Solares › {event_type}`
    - Containers: `#event-hero`, `#event-details`, `#event-note`, `#donki-link`
    - Carregar `js/detalhe-evento.js` como módulo ES
    - Botão "← Voltar para eventos solares" com link para `eventos.html`
    - _Requisitos: 2.1, 2.12, 2.13_
  - [x] 5.2 Criar `dashboard/js/detalhe-evento.js`
    - Extrair `id` da query string; se ausente, redirecionar para `eventos.html`
    - Chamar `fetchSolarEvent(id)` de `api.js`
    - Renderizar badge de tipo (CME/GST) com `typeBadgeStyle` (azul CME, âmbar GST)
    - Renderizar data formatada em português com `formatDatePT`
    - Renderizar badge de intensidade quando disponível
    - Renderizar campos condicionais: CME → velocidade, `is_earth_directed`, link DONKI; GST → `kp_index_max`
    - Renderizar nota/descrição quando disponível, com tag "NASA (EN)"
    - Renderizar link externo para NASA DONKI
    - Tratar erros: 404 → "Evento solar não encontrado.", outros → mensagem do erro
    - Importar `showSpinner`, `showError`, `setActiveNav` de `ui.js`
    - _Requisitos: 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11_

- [x] 6. Checkpoint — Verificar página de detalhe de evento solar
  - Garantir que todos os testes passam, perguntar ao usuário se houver dúvidas.

- [x] 7. Frontend — Cards clicáveis e filtros de data
  - [x] 7.1 Tornar cards de eventos clicáveis em `dashboard/js/eventos.js`
    - Envolver cada card em `<a href="detalhe-evento.html?id=${ev.event_id}">` com `text-decoration:none;color:inherit;cursor:pointer`
    - _Requisitos: 4.1, 4.2_
  - [x] 7.2 Adicionar campos de filtro de data em `dashboard/asteroides.html`
    - Adicionar dois `<input type="date">` (`#start-date` e `#end-date`) na div `#filters`
    - Labels "De:" e "Até:" seguindo o padrão visual dos filtros existentes
    - _Requisitos: 5.1_
  - [x] 7.3 Implementar lógica de filtro de data em `dashboard/js/asteroides.js`
    - Ler valores de `#start-date` e `#end-date`
    - Passar `start_date` e `end_date` para `fetchAsteroids` no `loadAsteroids`
    - Adicionar event listeners `change` nos inputs que resetam `currentOffset = 0` e chamam `loadAsteroids()`
    - _Requisitos: 5.2, 5.3, 5.4_

- [x] 8. Frontend — Testes de propriedade da página de detalhe
  - [ ]* 8.1 Escrever teste de propriedade para badge de tipo
    - **Propriedade 2: Badge de tipo renderiza estilo correto**
    - Criar `dashboard/tests/detalhe-evento.test.js`
    - Gerar eventos com tipo CME/GST, verificar que o HTML contém o texto do tipo e o estilo de cor correspondente
    - Mínimo 100 iterações com `fast-check`
    - **Valida: Requisitos 2.4**
  - [ ]* 8.2 Escrever teste de propriedade para formatação de data em português
    - **Propriedade 3: Formatação de data em português**
    - Gerar datas aleatórias no formato "YYYY-MM-DD", verificar que o resultado contém dia, mês em português e ano
    - Mínimo 100 iterações com `fast-check`
    - **Valida: Requisitos 2.5**
  - [ ]* 8.3 Escrever teste de propriedade para renderização condicional da nota
    - **Propriedade 4: Renderização condicional da nota**
    - Gerar eventos com/sem nota, verificar presença/ausência da seção de nota no HTML
    - Mínimo 100 iterações com `fast-check`
    - **Valida: Requisitos 2.6**
  - [ ]* 8.4 Escrever teste de propriedade para campos específicos por tipo
    - **Propriedade 5: Campos específicos por tipo de evento**
    - Gerar CMEs e verificar presença de velocidade, `is_earth_directed` e link DONKI; gerar GSTs e verificar presença de `kp_index_max` e ausência de campos CME
    - Mínimo 100 iterações com `fast-check`
    - **Valida: Requisitos 2.7, 2.8, 2.9**
  - [ ]* 8.5 Escrever teste de propriedade para link do card de evento
    - **Propriedade 7: Card de evento contém link para página de detalhe**
    - Gerar eventos solares, verificar que o HTML do card contém `href` apontando para `detalhe-evento.html?id={event_id}`
    - Mínimo 100 iterações com `fast-check`
    - **Valida: Requisitos 4.1**

- [x] 9. Frontend — Testes unitários
  - [ ]* 9.1 Escrever teste unitário para redirecionamento quando `id` ausente
    - Verificar que `detalhe-evento.js` redireciona para `eventos.html` quando o parâmetro `id` não está na URL
    - _Requisitos: 2.3_
  - [ ]* 9.2 Escrever teste unitário para exibição de erro 404
    - Verificar que a mensagem "Evento solar não encontrado." é exibida quando a API retorna 404
    - _Requisitos: 2.10_
  - [ ]* 9.3 Escrever teste unitário para exibição de erro genérico
    - Verificar que a mensagem de erro retornada pela API é exibida
    - _Requisitos: 2.11_
  - [ ]* 9.4 Escrever teste unitário para reset de paginação ao alterar data
    - Verificar que `currentOffset` é resetado para 0 quando o valor de um campo de data é alterado
    - _Requisitos: 5.3_

- [x] 10. Checkpoint final — Verificar todos os testes
  - Garantir que todos os testes passam, perguntar ao usuário se houver dúvidas.

## Notas

- Tarefas marcadas com `*` são opcionais e podem ser puladas para um MVP mais rápido
- Cada tarefa referencia requisitos específicos para rastreabilidade
- Checkpoints garantem validação incremental
- Testes de propriedade validam propriedades universais de corretude definidas no design
- Testes unitários validam exemplos específicos e edge cases
