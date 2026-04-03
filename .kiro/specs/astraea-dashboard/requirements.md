# Requirements Document

## Introduction

O Astraea Dashboard é uma interface web estática (HTML/CSS/JS puro, sem frameworks) que consome a API FastAPI existente em `http://localhost:8000`. O objetivo é apresentar dados de monitoramento de objetos próximos à Terra (NEOs) e eventos solares de forma clara, com tom visual de painel de controle científico dark. O dashboard é composto por 5 páginas HTML: home, lista de asteroides, detalhe de asteroide, eventos solares e sobre o projeto.

## Glossary

- **Dashboard**: Conjunto de 5 páginas HTML estáticas que compõem a interface do Astraea.
- **API**: Serviço FastAPI disponível em `http://localhost:8000`, que expõe os endpoints de asteroides, eventos solares e estatísticas.
- **NEO**: Near-Earth Object — objeto astronômico com órbita próxima à Terra.
- **CME**: Coronal Mass Ejection — ejeção de massa coronal, tipo de evento solar.
- **GST**: Geomagnetic Storm — tempestade geomagnética, tipo de evento solar.
- **LD**: Lunar Distance — distância lunar, unidade de medida de proximidade (~384.400 km).
- **Risk_Badge**: Elemento visual com texto ALTO, MÉDIO ou BAIXO e cor correspondente (vermelho, amarelo, verde).
- **Stat_Card**: Card de estatística com valor numérico, rótulo e tooltip explicativo.
- **Tooltip**: Elemento de texto explicativo exibido ao passar o cursor sobre o ícone "?".
- **Nav**: Barra de navegação presente em todas as páginas com logo ASTRAEA e links para as 5 páginas.
- **Status_Bar**: Faixa exibida na home indicando o estado do pipeline e a data da última coleta.
- **Countdown**: Contagem regressiva em dias/horas/minutos até a data de aproximação de um asteroide.
- **Design_System**: Conjunto de estilos definidos em `css/style.css`, incluindo paleta dark, tipografia Space Mono + Inter e componentes reutilizáveis.

---

## Requirements

### Requirement 1: Design System e Estrutura de Arquivos

**User Story:** Como desenvolvedor, quero um design system consistente e uma estrutura de arquivos organizada, para que o dashboard seja fácil de manter e visualmente coerente.

#### Acceptance Criteria

1. THE Dashboard SHALL organizar os arquivos na estrutura: `dashboard/index.html`, `dashboard/asteroides.html`, `dashboard/detalhe.html`, `dashboard/eventos.html`, `dashboard/sobre.html`, `dashboard/css/style.css`, `dashboard/js/config.js`, `dashboard/js/api.js`, `dashboard/js/home.js`, `dashboard/js/asteroides.js`, `dashboard/js/detalhe.js`, `dashboard/js/eventos.js`.
2. THE Design_System SHALL aplicar fundo escuro com cor de fundo `#0a0e1a` e cor de superfície `#111827` em todas as páginas.
3. THE Design_System SHALL utilizar a fonte Space Mono para números, labels, navegação e logo, e a fonte Inter (pesos 300, 400 e 500) para textos descritivos.
4. THE Design_System SHALL prefixar todos os labels de seção com `//` (ex: `// próximas aproximações`).
5. THE Risk_Badge SHALL exibir o texto ALTO com fundo vermelho (`#ef4444`), MÉDIO com fundo amarelo (`#f59e0b`) e BAIXO com fundo verde (`#22c55e`).
6. THE Design_System SHALL ser responsivo, adaptando o layout para telas com largura mínima de 320px.

---

### Requirement 2: Navegação Global

**User Story:** Como usuário, quero uma barra de navegação consistente em todas as páginas, para que eu possa me orientar e navegar entre as seções do dashboard.

#### Acceptance Criteria

1. THE Nav SHALL estar presente em todas as 5 páginas HTML do Dashboard.
2. THE Nav SHALL exibir o logo "ASTRAEA" em Space Mono e links para: Home (`index.html`), Asteroides (`asteroides.html`), Eventos Solares (`eventos.html`) e Sobre (`sobre.html`).
3. THE Nav SHALL destacar visualmente o link correspondente à página atualmente ativa.
4. THE Nav SHALL ser acessível via teclado, com todos os links navegáveis por Tab e ativáveis por Enter.

---

### Requirement 3: Página Home — Visão Geral

**User Story:** Como usuário, quero uma página inicial com resumo do sistema, para que eu possa ter uma visão rápida do estado atual do monitoramento.

#### Acceptance Criteria

1. WHEN a página `index.html` é carregada, THE Dashboard SHALL exibir uma Status_Bar com um indicador visual pulsante verde e o texto "Pipeline ativo — última coleta: [data]".
2. WHEN a página `index.html` é carregada, THE Dashboard SHALL exibir um hero com o texto "X objetos próximos à Terra rastreados nos próximos 7 dias", onde X é o número de itens retornados pelo endpoint `GET /v1/asteroids/upcoming`.
3. WHEN a página `index.html` é carregada, THE Dashboard SHALL exibir 4 Stat_Cards com os valores de `total_asteroids`, `hazardous_count`, `closest_approach_lunar` (com `closest_asteroid_name`) e `total_solar_events`, obtidos do endpoint `GET /v1/stats/summary`.
4. THE Dashboard SHALL exibir um Tooltip explicativo em português ao passar o cursor sobre o ícone "?" de cada Stat_Card.
5. WHEN a página `index.html` é carregada, THE Dashboard SHALL exibir uma tabela de próximas aproximações com os dados de `GET /v1/asteroids/upcoming`, contendo as colunas: nome do asteroide, data de aproximação, distância em LD e km, velocidade em km/s, diâmetro estimado em km e Risk_Badge.
6. WHEN o usuário clica em uma linha da tabela de próximas aproximações, THE Dashboard SHALL navegar para `detalhe.html?id={neo_id}`.
7. WHEN a página `index.html` é carregada, THE Dashboard SHALL exibir os 3 eventos solares mais recentes obtidos de `GET /v1/solar-events?limit=3`, cada um com tipo, data, detalhes disponíveis e explicação em português.
8. THE Dashboard SHALL exibir um footer com créditos do projeto e link para o repositório GitHub.
9. IF o endpoint `GET /v1/stats/summary` retornar erro, THEN THE Dashboard SHALL exibir uma mensagem de erro em português no lugar dos Stat_Cards afetados.
10. IF o endpoint `GET /v1/asteroids/upcoming` retornar erro, THEN THE Dashboard SHALL exibir uma mensagem de erro em português no lugar da tabela de próximas aproximações.

---

### Requirement 4: Página Asteroides — Lista Completa

**User Story:** Como usuário, quero visualizar e filtrar a lista completa de asteroides monitorados, para que eu possa encontrar objetos específicos por nível de risco.

#### Acceptance Criteria

1. WHEN a página `asteroides.html` é carregada, THE Dashboard SHALL buscar e exibir asteroides do endpoint `GET /v1/asteroids` com `limit=50` e `offset=0`.
2. THE Dashboard SHALL exibir filtros de risco com as opções: Todos, Alto, Médio e Baixo, que ao serem selecionados enviam o parâmetro `risk_label` para o endpoint `GET /v1/asteroids`.
3. THE Dashboard SHALL exibir um checkbox "Apenas perigosos" que, quando marcado, envia `hazardous=true` para o endpoint `GET /v1/asteroids`.
4. WHEN o usuário aplica um filtro, THE Dashboard SHALL recarregar a tabela com os dados filtrados sem recarregar a página.
5. THE Dashboard SHALL exibir paginação com botões "Anterior" e "Próximo" que incrementam e decrementam o parâmetro `offset` em 50 unidades.
6. WHEN o usuário clica em uma linha da tabela de asteroides, THE Dashboard SHALL navegar para `detalhe.html?id={neo_id}`.
7. IF o endpoint `GET /v1/asteroids` retornar erro, THEN THE Dashboard SHALL exibir uma mensagem de erro em português no lugar da tabela.

---

### Requirement 5: Página Detalhe — Asteroide Individual

**User Story:** Como usuário, quero visualizar todos os dados disponíveis de um asteroide específico, para que eu possa entender seu nível de risco e características orbitais.

#### Acceptance Criteria

1. WHEN a página `detalhe.html` é carregada, THE Dashboard SHALL ler o parâmetro `id` da URL (`?id=NEO_ID`) e buscar os dados do endpoint `GET /v1/asteroids/{neo_id}`.
2. THE Dashboard SHALL exibir um breadcrumb com o caminho "Home > Asteroides > [nome do asteroide]".
3. THE Dashboard SHALL exibir um hero com o nome do asteroide e tags indicando se é potencialmente perigoso e o `risk_label_ml`.
4. WHEN a data de `close_approach_date` for posterior à data atual, THE Dashboard SHALL exibir um Countdown com dias, horas e minutos restantes até a aproximação.
5. THE Dashboard SHALL exibir 6 Metric_Cards com Tooltip explicativo em português para cada um dos seguintes valores: `miss_distance_lunar`, `miss_distance_km`, `relative_velocity_km_s`, `estimated_diameter_min_km` e `estimated_diameter_max_km`, e `absolute_magnitude_h`.
6. THE Dashboard SHALL exibir um painel de risco ML com o valor de `risk_score_ml` em uma barra de progresso e o `risk_label_ml` como Risk_Badge.
7. THE Dashboard SHALL exibir um link externo para a página do asteroide no NASA JPL Small-Body Database, usando a URL `https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr={neo_id}`.
8. IF o endpoint `GET /v1/asteroids/{neo_id}` retornar erro 404, THEN THE Dashboard SHALL exibir uma mensagem "Asteroide não encontrado" em português.
9. IF o parâmetro `id` estiver ausente na URL, THEN THE Dashboard SHALL redirecionar o usuário para `asteroides.html`.

---

### Requirement 6: Página Eventos Solares

**User Story:** Como usuário, quero visualizar os eventos solares registrados com filtro por tipo, para que eu possa acompanhar CMEs e tempestades geomagnéticas.

#### Acceptance Criteria

1. WHEN a página `eventos.html` é carregada, THE Dashboard SHALL buscar e exibir eventos do endpoint `GET /v1/solar-events?limit=50`.
2. THE Dashboard SHALL exibir filtros de tipo com as opções: Todos, CME e GST, que ao serem selecionados enviam o parâmetro `event_type` para o endpoint `GET /v1/solar-events`.
3. WHEN o usuário aplica um filtro de tipo, THE Dashboard SHALL recarregar os cards de eventos sem recarregar a página.
4. THE Dashboard SHALL exibir cada evento como um card contendo: tipo (`event_type`), data (`event_date`), velocidade (`speed_km_s`) quando disponível, índice Kp (`kp_index_max`) quando disponível, `intensity_label` como Risk_Badge e nota (`note`) quando disponível.
5. THE Dashboard SHALL exibir uma explicação em português sobre o que é CME e o que é GST na página de eventos.
6. IF o endpoint `GET /v1/solar-events` retornar erro, THEN THE Dashboard SHALL exibir uma mensagem de erro em português no lugar dos cards de eventos.

---

### Requirement 7: Página Sobre

**User Story:** Como usuário, quero entender o projeto Astraea, sua stack técnica e as fontes de dados utilizadas, para que eu possa avaliar a confiabilidade das informações apresentadas.

#### Acceptance Criteria

1. THE Dashboard SHALL exibir na página `sobre.html` uma explicação do projeto Astraea em português acessível, sem jargão técnico excessivo.
2. THE Dashboard SHALL listar a stack técnica do projeto: FastAPI, dbt, PostgreSQL, scikit-learn, Python e HTML/CSS/JS.
3. THE Dashboard SHALL exibir as fontes de dados utilizadas: NASA NeoWs e NASA DONKI, com links externos para as respectivas páginas oficiais.
4. THE Dashboard SHALL exibir um link para o repositório GitHub do projeto.

---

### Requirement 8: Consumo da API e Tratamento de Erros

**User Story:** Como desenvolvedor, quero que todas as chamadas à API sejam centralizadas e com tratamento de erros consistente, para que o dashboard seja robusto e fácil de manter.

#### Acceptance Criteria

1. THE Dashboard SHALL centralizar todas as chamadas à API no arquivo `js/api.js`, utilizando as funções `fetchUpcoming`, `fetchAsteroids`, `fetchAsteroid`, `fetchSolarEvents`, `fetchEarthDirected` e `fetchStats`.
2. THE Dashboard SHALL ler a URL base da API a partir da constante `CONFIG.API_BASE_URL` definida em `js/config.js`.
3. IF qualquer chamada à API retornar um status HTTP diferente de 2xx, THEN THE Dashboard SHALL exibir uma mensagem de erro em português descrevendo o problema ao usuário.
4. WHILE uma chamada à API estiver em andamento, THE Dashboard SHALL exibir um indicador visual de carregamento (spinner ou skeleton) no lugar do conteúdo que está sendo carregado.
5. THE Dashboard SHALL carregar os arquivos `js/config.js` e `js/api.js` antes dos demais scripts em todas as páginas que consomem a API.
