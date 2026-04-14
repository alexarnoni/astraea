# Documento de Requisitos — Astraea v1.1

## Introdução

Este documento especifica os requisitos para a release v1.1 do Astraea, abrangendo três funcionalidades: (1) endpoint de detalhe de evento solar na API, (2) página de detalhe de evento solar no frontend, e (3) filtro por data na página de asteroides. O escopo é limitado à API FastAPI (`api/`) e ao dashboard Vanilla JS (`dashboard/`). Pipeline, dbt e ML estão fora do escopo.

## Glossário

- **API**: Aplicação FastAPI em `api/main.py` que serve dados sob o prefixo `/v1/`
- **Dashboard**: Frontend Vanilla JS em `dashboard/` que consome a API
- **Evento_Solar**: Registro na tabela `mart.mart_solar_events`, representando uma ejeção de massa coronal (CME) ou tempestade geomagnética (GST)
- **SolarEventResponse**: Modelo Pydantic que define a estrutura de resposta JSON para eventos solares
- **Card_Evento**: Componente visual em `eventos.js` que renderiza um evento solar na listagem
- **Página_Detalhe_Evento**: Página HTML (`detalhe-evento.html`) + JS (`detalhe-evento.js`) que exibe informações completas de um evento solar
- **Filtro_Data**: Par de campos de entrada (data início e data fim) que restringe os resultados da listagem de asteroides
- **DONKI**: API da NASA (Database Of Notifications, Knowledge, Information) que fornece dados de eventos solares
- **Rate_Limiter**: Mecanismo slowapi configurado em `main.py` que limita requisições a 60 por minuto por IP

## Requisitos

### Requisito 1: Endpoint de detalhe de evento solar

**User Story:** Como desenvolvedor do frontend, quero buscar os dados completos de um evento solar pelo seu ID, para que a página de detalhe possa exibir todas as informações disponíveis.

#### Critérios de Aceitação

1. WHEN uma requisição GET é recebida em `/v1/solar-events/{event_id}` com um `event_id` existente na tabela `mart.mart_solar_events`, THE API SHALL retornar status 200 com um JSON contendo todos os campos do modelo SolarEventResponse
2. WHEN uma requisição GET é recebida em `/v1/solar-events/{event_id}` com um `event_id` que não existe na tabela `mart.mart_solar_events`, THE API SHALL retornar status 404 com uma mensagem descritiva no campo `detail`
3. THE Rate_Limiter SHALL aplicar o limite de 60 requisições por minuto ao endpoint `/v1/solar-events/{event_id}`, seguindo o mesmo padrão dos demais endpoints
4. THE API SHALL incluir o campo `is_earth_directed` (booleano, nullable) no modelo SolarEventResponse, refletindo o dado disponível na tabela `mart.mart_solar_events`
5. WHEN o endpoint `/v1/solar-events/{event_id}` é chamado, THE API SHALL buscar o registro por `event_id` na tabela `mart.mart_solar_events` usando query parametrizada

### Requisito 2: Página de detalhe de evento solar no frontend

**User Story:** Como usuário do dashboard, quero visualizar os detalhes completos de um evento solar, para que eu possa entender suas características e impacto potencial.

#### Critérios de Aceitação

1. THE Dashboard SHALL disponibilizar uma página `detalhe-evento.html` que carrega o script `detalhe-evento.js` como módulo ES
2. WHEN a página `detalhe-evento.html` é carregada com o parâmetro de query `id` presente, THE Página_Detalhe_Evento SHALL chamar a função `fetchSolarEvent(eventId)` de `api.js` para buscar os dados do evento
3. WHEN a página `detalhe-evento.html` é carregada sem o parâmetro de query `id`, THE Página_Detalhe_Evento SHALL redirecionar o usuário para `eventos.html`
4. WHEN os dados do evento são carregados com sucesso, THE Página_Detalhe_Evento SHALL exibir um badge visual indicando o tipo do evento (CME ou GST) usando o mesmo estilo de cores definido em `eventos.js`
5. WHEN os dados do evento são carregados com sucesso, THE Página_Detalhe_Evento SHALL exibir a data do evento formatada em português
6. WHEN os dados do evento são carregados com sucesso, THE Página_Detalhe_Evento SHALL exibir a descrição completa do evento (campo `note`) quando disponível
7. WHEN o evento carregado é do tipo CME, THE Página_Detalhe_Evento SHALL exibir os campos específicos: velocidade (`speed_km_s`), flag de direcionamento à Terra (`is_earth_directed`) e link para análise no DONKI
8. WHEN o evento carregado é do tipo GST, THE Página_Detalhe_Evento SHALL exibir o campo específico: índice Kp máximo (`kp_index_max`)
9. THE Página_Detalhe_Evento SHALL exibir um link externo para a fonte NASA DONKI do evento
10. WHEN a chamada à API falha com status 404, THE Página_Detalhe_Evento SHALL exibir uma mensagem de erro informando que o evento não foi encontrado
11. WHEN a chamada à API falha por outro motivo, THE Página_Detalhe_Evento SHALL exibir a mensagem de erro retornada
12. THE Página_Detalhe_Evento SHALL incluir breadcrumb de navegação com links para "Visão geral" (index.html) e "Eventos Solares" (eventos.html), seguindo o padrão de `detalhe.html`
13. THE Página_Detalhe_Evento SHALL incluir a barra de navegação (nav), footer e bottom nav mobile, seguindo o padrão das demais páginas do dashboard

### Requisito 3: Função fetchSolarEvent em api.js

**User Story:** Como desenvolvedor do frontend, quero uma função centralizada para buscar um evento solar por ID, para que a chamada à API siga o padrão existente em `api.js`.

#### Critérios de Aceitação

1. THE Dashboard SHALL disponibilizar a função `fetchSolarEvent(eventId)` exportada de `api.js`, que chama `GET /v1/solar-events/{eventId}` usando a função `apiFetch` existente
2. WHEN a função `fetchSolarEvent` recebe um `eventId`, THE Dashboard SHALL construir a URL no formato `/v1/solar-events/${eventId}` e delegar a chamada para `apiFetch`

### Requisito 4: Cards de eventos clicáveis na listagem

**User Story:** Como usuário do dashboard, quero clicar em um card de evento solar na listagem para navegar à página de detalhe, para que eu possa ver informações completas do evento.

#### Critérios de Aceitação

1. WHEN a listagem de eventos solares é renderizada em `eventos.js`, THE Dashboard SHALL tornar cada Card_Evento um link clicável que navega para `detalhe-evento.html?id={event_id}`
2. WHEN o usuário passa o cursor sobre um Card_Evento, THE Dashboard SHALL indicar visualmente que o card é clicável (cursor pointer)

### Requisito 5: Filtro por data na página de asteroides

**User Story:** Como usuário do dashboard, quero filtrar asteroides por intervalo de datas, para que eu possa analisar objetos de um período específico.

#### Critérios de Aceitação

1. THE Dashboard SHALL exibir dois campos de entrada de data (`start_date` e `end_date`) na área de filtros existente da página `asteroides.html`, seguindo o padrão visual dos filtros de risco e perigosidade
2. WHEN o usuário preenche o campo `start_date` e/ou `end_date`, THE Dashboard SHALL incluir os parâmetros `start_date` e/ou `end_date` na query string da chamada a `fetchAsteroids` em `api.js`
3. WHEN o usuário altera o valor de um campo de data, THE Dashboard SHALL resetar a paginação para a primeira página e recarregar a listagem de asteroides
4. WHEN ambos os campos de data estão vazios, THE Dashboard SHALL omitir os parâmetros `start_date` e `end_date` da query string, retornando ao comportamento padrão sem filtro de data
5. THE Dashboard SHALL passar os parâmetros `start_date` e `end_date` na função `fetchAsteroids` de `api.js`, adicionando-os ao `URLSearchParams` quando preenchidos
