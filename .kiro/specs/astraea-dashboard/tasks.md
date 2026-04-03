# Implementation Plan: Astraea Dashboard

## Overview

Implementação incremental do dashboard web estático em HTML/CSS/JS puro. Cada tarefa constrói sobre a anterior, começando pela base (design system + config + api.js), passando pelas páginas individuais e terminando com a suíte de testes.

## Tasks

- [x] 1. Configurar estrutura de arquivos e design system
  - Criar todos os 12 arquivos do dashboard com estrutura mínima: `dashboard/index.html`, `dashboard/asteroides.html`, `dashboard/detalhe.html`, `dashboard/eventos.html`, `dashboard/sobre.html`, `dashboard/css/style.css`, `dashboard/js/config.js`, `dashboard/js/api.js`, `dashboard/js/home.js`, `dashboard/js/asteroides.js`, `dashboard/js/detalhe.js`, `dashboard/js/eventos.js`
  - Implementar `css/style.css` com paleta dark (`#0a0e1a`, `#111827`), fontes Space Mono + Inter via Google Fonts CDN, componentes `.badge--alto/médio/baixo`, `.spinner`, `.error-msg`, `.stat-card`, `.metric-card`, `.nav`, `.status-bar`, `.countdown`, layout responsivo (min 320px)
  - Prefixar labels de seção com `//` no CSS/HTML
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 2. Implementar `js/config.js` e `js/api.js`
  - [x] 2.1 Criar `js/config.js` exportando `CONFIG.API_BASE_URL = "http://localhost:8000/v1"`
    - _Requirements: 8.2_
  - [x] 2.2 Criar `js/api.js` com função interna `apiFetch(path)` e as 6 funções exportadas: `fetchStats`, `fetchUpcoming`, `fetchAsteroids`, `fetchAsteroid`, `fetchSolarEvents`, `fetchEarthDirected`
    - `apiFetch` deve lançar `Error` com mensagem em português para status não-2xx
    - `fetchAsteroids` e `fetchSolarEvents` devem omitir params `null`/`undefined` da query string
    - _Requirements: 8.1, 8.2, 8.3_
  - [ ]* 2.3 Escrever teste de propriedade P7: Erro HTTP → mensagem em português
    - **Property 7: Tratamento de erro HTTP exibe mensagem em português**
    - **Validates: Requirements 3.9, 3.10, 4.7, 6.6, 8.3**
  - [ ]* 2.4 Escrever teste de propriedade P8: Query string de filtros de asteroides
    - **Property 8: Construção de query string de filtros de asteroides**
    - **Validates: Requirements 4.2, 4.3**
  - [ ]* 2.5 Escrever teste de propriedade P15: Query string de filtro de eventos solares
    - **Property 15: Construção de query string de filtro de eventos solares**
    - **Validates: Requirements 6.2**
  - [ ]* 2.6 Escrever teste de propriedade P16: Funções de fetch usam CONFIG.API_BASE_URL como prefixo
    - **Property 16: Funções de fetch usam CONFIG.API_BASE_URL como prefixo**
    - **Validates: Requirements 8.2**

- [x] 3. Implementar componentes visuais reutilizáveis em `js/ui.js`
  - Criar `dashboard/js/ui.js` exportando: `renderRiskBadge(label)`, `renderStatCard(value, label, tooltip)`, `renderMetricCard(value, label, tooltip)`, `showSpinner(container)`, `showError(container, message)`, `setActiveNav(filename)`, `renderCountdown(dateStr)`
  - `setActiveNav` deve comparar `filename` com `location.pathname` e adicionar classe `.active` ao link correspondente
  - `renderCountdown` deve calcular dias/horas/minutos restantes e retornar `null` para datas passadas
  - _Requirements: 1.5, 2.3, 3.4, 5.4, 8.4_
  - [ ]* 3.1 Escrever teste de propriedade P1: Risk Badge mapeia label para classe CSS correta
    - **Property 1: Risk Badge mapeia label para classe CSS correta**
    - **Validates: Requirements 1.5**
  - [ ]* 3.2 Escrever teste de propriedade P2: Link ativo na navegação corresponde à página atual
    - **Property 2: Link ativo na navegação corresponde à página atual**
    - **Validates: Requirements 2.3**
  - [ ]* 3.3 Escrever teste de propriedade P12: Countdown retorna valores positivos para datas futuras
    - **Property 12: Countdown retorna valores positivos para datas futuras**
    - **Validates: Requirements 5.4**

- [x] 4. Checkpoint — Garantir que config, api e ui estão funcionando
  - Garantir que todos os testes passam, perguntar ao usuário se houver dúvidas.

- [x] 5. Implementar navegação global (Nav + Footer) nos HTMLs
  - Adicionar `<nav>` com logo "ASTRAEA" e links para as 4 páginas em todos os 5 HTMLs
  - Adicionar `<footer>` com créditos e link para GitHub em todos os HTMLs
  - Cada página deve carregar `config.js` e `api.js` antes do script de página via `<script type="module">`
  - _Requirements: 2.1, 2.2, 2.4, 3.8, 8.5_
  - [ ]* 5.1 Escrever testes unitários de estrutura HTML
    - Verificar que todos os 12 arquivos existem
    - Verificar presença de `<nav>`, `<footer>` e links corretos em cada HTML
    - _Requirements: 1.1, 2.1, 2.2_

- [x] 6. Implementar página Home (`index.html` + `js/home.js`)
  - [x] 6.1 Implementar Status_Bar com indicador pulsante e texto "Pipeline ativo — última coleta: [data]"
    - _Requirements: 3.1_
  - [x] 6.2 Implementar hero com contagem de upcoming asteroids via `fetchUpcoming`
    - _Requirements: 3.2_
  - [x] 6.3 Implementar 4 Stat_Cards com dados de `fetchStats` e tooltips em português
    - Cards: `total_asteroids`, `hazardous_count`, `closest_approach_lunar` (com nome), `total_solar_events`
    - _Requirements: 3.3, 3.4_
  - [x] 6.4 Implementar tabela de próximas aproximações com colunas obrigatórias e navegação para `detalhe.html?id=`
    - Colunas: nome, data, distância LD, distância km, velocidade km/s, diâmetro km, Risk_Badge
    - _Requirements: 3.5, 3.6_
  - [x] 6.5 Implementar cards dos 3 eventos solares mais recentes via `fetchSolarEvents({ limit: 3 })`
    - _Requirements: 3.7_
  - [x] 6.6 Implementar tratamento de erro com `showError` para todos os containers da home
    - _Requirements: 3.9, 3.10_
  - [ ]* 6.7 Escrever teste de propriedade P3: Hero reflete contagem real de upcoming asteroids
    - **Property 3: Hero da home reflete contagem real de upcoming asteroids**
    - **Validates: Requirements 3.2**
  - [ ]* 6.8 Escrever teste de propriedade P4: Stat Cards renderizam todos os valores com tooltips
    - **Property 4: Stat Cards renderizam todos os valores de StatsResponse com tooltips**
    - **Validates: Requirements 3.3, 3.4**
  - [ ]* 6.9 Escrever teste de propriedade P5: Tabela de upcoming contém todas as colunas obrigatórias
    - **Property 5: Tabela de upcoming contém todas as colunas obrigatórias**
    - **Validates: Requirements 3.5**
  - [ ]* 6.10 Escrever teste de propriedade P6: Cards de eventos solares contêm os campos disponíveis
    - **Property 6: Cards de eventos solares contêm os campos disponíveis**
    - **Validates: Requirements 3.7, 6.4**

- [x] 7. Implementar página Asteroides (`asteroides.html` + `js/asteroides.js`)
  - [x] 7.1 Implementar busca inicial com `fetchAsteroids({ limit: 50, offset: 0 })` e renderização da tabela
    - _Requirements: 4.1_
  - [x] 7.2 Implementar filtros de risco (Todos/Alto/Médio/Baixo) e checkbox "Apenas perigosos" com re-fetch sem reload
    - _Requirements: 4.2, 4.3, 4.4_
  - [x] 7.3 Implementar paginação com botões "Anterior" e "Próximo" incrementando/decrementando `offset` em 50
    - _Requirements: 4.5_
  - [x] 7.4 Implementar navegação para `detalhe.html?id=` ao clicar em linha da tabela
    - _Requirements: 4.6_
  - [x] 7.5 Implementar tratamento de erro com `showError`
    - _Requirements: 4.7_
  - [ ]* 7.6 Escrever teste de propriedade P9: Paginação incrementa e decrementa offset em 50
    - **Property 9: Paginação incrementa e decrementa offset em 50**
    - **Validates: Requirements 4.5**

- [x] 8. Checkpoint — Garantir que home e asteroides funcionam corretamente
  - Garantir que todos os testes passam, perguntar ao usuário se houver dúvidas.

- [x] 9. Implementar página Detalhe (`detalhe.html` + `js/detalhe.js`)
  - [x] 9.1 Implementar extração de `?id=` da URL e redirecionamento para `asteroides.html` se ausente
    - _Requirements: 5.1, 5.9_
  - [x] 9.2 Implementar breadcrumb "Home > Asteroides > [nome]" e hero com nome + tags de risco
    - _Requirements: 5.2, 5.3_
  - [x] 9.3 Implementar Countdown via `setInterval` para datas futuras
    - _Requirements: 5.4_
  - [x] 9.4 Implementar 6 Metric_Cards com tooltips em português para os campos de distância, velocidade, diâmetro e magnitude
    - _Requirements: 5.5_
  - [x] 9.5 Implementar painel ML com barra de progresso (`risk_score_ml`) e Risk_Badge (`risk_label_ml`)
    - _Requirements: 5.6_
  - [x] 9.6 Implementar link externo para NASA JPL com URL `https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr={neo_id}`
    - _Requirements: 5.7_
  - [x] 9.7 Implementar tratamento de erro 404 com mensagem "Asteroide não encontrado."
    - _Requirements: 5.8_
  - [ ]* 9.8 Escrever teste de propriedade P10: Extração de parâmetro `id` da URL
    - **Property 10: Extração de parâmetro `id` da URL**
    - **Validates: Requirements 5.1, 5.9**
  - [ ]* 9.9 Escrever teste de propriedade P11: Breadcrumb contém o nome do asteroide
    - **Property 11: Breadcrumb contém o nome do asteroide**
    - **Validates: Requirements 5.2**
  - [ ]* 9.10 Escrever teste de propriedade P13: Painel ML exibe risk_score_ml e risk_label_ml corretamente
    - **Property 13: Painel ML exibe risk_score_ml e risk_label_ml corretamente**
    - **Validates: Requirements 5.6**
  - [ ]* 9.11 Escrever teste de propriedade P14: URL do NASA JPL contém o neo_id correto
    - **Property 14: URL do NASA JPL contém o neo_id correto**
    - **Validates: Requirements 5.7**

- [x] 10. Implementar página Eventos Solares (`eventos.html` + `js/eventos.js`)
  - [x] 10.1 Implementar busca inicial com `fetchSolarEvents({ limit: 50 })` e renderização dos cards
    - _Requirements: 6.1_
  - [x] 10.2 Implementar filtros de tipo (Todos/CME/GST) com re-fetch sem reload
    - _Requirements: 6.2, 6.3_
  - [x] 10.3 Implementar cards de eventos com todos os campos condicionais (`speed_km_s`, `kp_index_max`, `intensity_label`, `note`)
    - _Requirements: 6.4_
  - [x] 10.4 Adicionar explicação em português sobre CME e GST na página
    - _Requirements: 6.5_
  - [x] 10.5 Implementar tratamento de erro com `showError`
    - _Requirements: 6.6_

- [x] 11. Implementar página Sobre (`sobre.html`)
  - Adicionar conteúdo estático: explicação do projeto em português, stack técnica (FastAPI, dbt, PostgreSQL, scikit-learn, Python, HTML/CSS/JS), fontes de dados (NASA NeoWs + NASA DONKI com links externos) e link para GitHub
  - _Requirements: 7.1, 7.2, 7.3, 7.4_
  - [ ]* 11.1 Escrever testes unitários para `sobre.html`
    - Verificar presença de stack técnica, links para NASA NeoWs e DONKI, e link para GitHub
    - _Requirements: 7.2, 7.3, 7.4_

- [x] 12. Configurar Vitest e executar suíte completa de testes
  - Criar `dashboard/vitest.config.js` com `{ test: { globals: true } }`
  - Criar `dashboard/package.json` com dependências `vitest` e `fast-check`
  - Organizar todos os testes em `dashboard/tests/` com arquivos separados por módulo
  - Garantir que cada teste de propriedade contém a tag `// Feature: astraea-dashboard, Property N: <texto>`
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 13. Checkpoint final — Garantir que todos os testes passam
  - Garantir que todos os testes passam, perguntar ao usuário se houver dúvidas.

## Notes

- Tarefas marcadas com `*` são opcionais e podem ser puladas para um MVP mais rápido
- Cada tarefa referencia os requisitos específicos para rastreabilidade
- `js/ui.js` é um arquivo adicional não listado nos 12 originais, mas necessário para centralizar os componentes reutilizáveis
- Testes de propriedade usam `fast-check` com mínimo de 100 iterações (`numRuns: 100`)
- Executar testes com `npx vitest --run` dentro do diretório `dashboard/`
