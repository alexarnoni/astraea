# Plano de Implementação: api-rate-limiting

## Visão Geral

Adicionar rate limiting por IP à API Astraea usando `slowapi` em memória, limitando a 60 req/min por IP real extraído do header `X-Forwarded-For`. Todos os endpoints `/v1/` são limitados; `/` e `/health` ficam excluídos.

## Tasks

- [x] 1. Adicionar slowapi ao requirements.txt
  - Declarar `slowapi==0.1.9` como dependência pinada em `api/requirements.txt`
  - _Requirements: 1.1, 1.2_

- [x] 2. Implementar o Rate Limiter em main.py
  - [x] 2.1 Criar a função `get_client_ip(request: Request) -> str` em `api/main.py`
    - Ler `X-Forwarded-For`; se presente, retornar o primeiro IP (split por `,` + strip)
    - Fallback para `request.client.host` quando o header estiver ausente
    - _Requirements: 2.2, 2.3, 2.4, 5.1, 5.2_

  - [ ]* 2.2 Escrever property test para `get_client_ip` (Property 1)
    - **Property 1: Extração do IP real do X-Forwarded-For**
    - **Validates: Requirements 2.2, 2.4, 5.1, 5.2**
    - Usar `hypothesis` com `st.ip_addresses()`, min 100 exemplos
    - Arquivo: `api/tests/test_rate_limiting.py`

  - [x] 2.3 Instanciar `Limiter` e registrar middleware e handler em `api/main.py`
    - `limiter = Limiter(key_func=get_client_ip)`
    - `app.state.limiter = limiter`
    - `app.add_middleware(SlowAPIMiddleware)`
    - Registrar `_rate_limit_exceeded_handler` para `RateLimitExceeded`
    - Handler retorna JSON `{"error": "Rate limit exceeded: 60 per 1 minute"}` com header `Retry-After`
    - _Requirements: 2.1, 2.5, 2.6, 4.1, 4.2, 4.3, 4.4_

- [x] 3. Aplicar decorator `@limiter.limit("60/minute")` nos routers
  - [x] 3.1 Decorar todos os endpoints em `api/routers/asteroids.py`
    - Adicionar `request: Request` como parâmetro em cada função de endpoint
    - Adicionar `@limiter.limit("60/minute")` em cada endpoint
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 3.2 Decorar todos os endpoints em `api/routers/solar_events.py`
    - Adicionar `request: Request` como parâmetro em cada função de endpoint
    - Adicionar `@limiter.limit("60/minute")` em cada endpoint
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 3.3 Decorar o endpoint em `api/routers/stats.py`
    - Adicionar `request: Request` como parâmetro na função de endpoint
    - Adicionar `@limiter.limit("60/minute")` no endpoint
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 4. Checkpoint — Garantir que a aplicação sobe sem erros
  - Garantir que todos os imports estão corretos e a aplicação inicializa sem erros. Perguntar ao usuário se houver dúvidas.

- [x] 5. Criar testes em api/tests/test_rate_limiting.py
  - [x] 5.1 Escrever testes de exemplo (pytest) para configuração e endpoints excluídos
    - Verificar que `app.state.limiter` está configurado
    - Verificar que `SlowAPIMiddleware` está registrado
    - Verificar que handler de `RateLimitExceeded` está registrado
    - Verificar que `GET /` e `GET /health` retornam 200 mesmo após 61+ requisições
    - _Requirements: 2.5, 2.6, 4.4, 6.1, 6.2_

  - [x] 5.2 Escrever testes de exemplo para o comportamento do limite
    - Verificar que a 60ª requisição para `/v1/asteroids` retorna 200
    - Verificar que a 61ª requisição retorna 429
    - _Requirements: 3.4, 3.5, 7.1, 7.2_

  - [ ]* 5.3 Escrever property test para limite de requisições (Property 2)
    - **Property 2: Limite de requisições por IP**
    - **Validates: Requirements 3.1, 3.5, 4.1**
    - `@given(ip=st.ip_addresses(v=4).map(str))`, 20 exemplos
    - Resetar estado do limiter entre exemplos

  - [ ]* 5.4 Escrever property test para formato da resposta 429 (Property 3)
    - **Property 3: Formato da resposta 429**
    - **Validates: Requirements 4.2, 4.3**
    - Verificar campo `error` e header `Retry-After` com valor inteiro positivo
    - `@given(ip=st.ip_addresses(v=4).map(str))`, 20 exemplos

  - [ ]* 5.5 Escrever property test para isolamento de contadores por IP (Property 4)
    - **Property 4: Isolamento de contadores por IP**
    - **Validates: Requirements 5.3, 5.4, 7.4, 7.5**
    - `@given(ip_a, ip_b)` com `assume(ip_a != ip_b)`, 20 exemplos
    - Esgotar limite para `ip_a`; verificar que `ip_b` ainda retorna 200

- [x] 6. Checkpoint final — Garantir que todos os testes passam
  - Garantir que todos os testes passam. Perguntar ao usuário se houver dúvidas.

## Notas

- Tasks marcadas com `*` são opcionais e podem ser puladas para um MVP mais rápido
- Cada task referencia os requisitos específicos para rastreabilidade
- O `request: Request` é obrigatório em cada endpoint decorado com `@limiter.limit`
- O `limiter` deve ser importado nos routers a partir de `main` (ex: `from main import limiter`)
- Resetar o estado do limiter nos testes: `app.state.limiter._storage.reset()` ou recriar o app entre exemplos
