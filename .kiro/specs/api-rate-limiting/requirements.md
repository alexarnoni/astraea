# Requirements Document

## Introduction

A feature `api-rate-limiting` adiciona controle de taxa de requisições à API Astraea, limitando cada cliente a 60 requisições por minuto por endereço IP. A API é pública, read-only, e roda atrás do Nginx como proxy reverso em Oracle VM. O rate limiting é implementado em memória usando `slowapi`, sem dependência de Redis ou banco externo. O IP real do cliente é extraído do header `X-Forwarded-For` injetado pelo Nginx. Quando o limite é excedido, a API retorna HTTP 429 com mensagem descritiva.

## Glossary

- **Rate_Limiter**: instância de `slowapi.Limiter` configurada com a chave de IP real do cliente
- **API**: aplicação FastAPI do projeto Astraea, rodando na porta 8002
- **Client_IP**: endereço IPv4 ou IPv6 do cliente final, extraído do header `X-Forwarded-For` quando presente, ou do IP de conexão direta como fallback
- **Rate_Limit_Window**: janela de tempo de 60 segundos usada para contagem de requisições por IP
- **Rate_Limit_Counter**: contador em memória mantido pelo Rate_Limiter para cada Client_IP dentro da Rate_Limit_Window
- **Nginx**: proxy reverso que encaminha requisições para a API e injeta o header `X-Forwarded-For` com o IP real do cliente
- **Endpoint**: qualquer rota registrada sob o prefixo `/v1/` da API

---

## Requirements

### Requirement 1: Instalação da Dependência

**User Story:** As a developer, I want `slowapi` declared in `requirements.txt`, so that the rate limiting dependency is reproducible across environments.

#### Acceptance Criteria

1. THE `api/requirements.txt` SHALL declare `slowapi==0.1.9` como dependência pinada.
2. THE API SHALL ser executável após `pip install -r api/requirements.txt` sem etapas manuais adicionais.

---

### Requirement 2: Inicialização do Rate Limiter

**User Story:** As a developer, I want the Rate_Limiter initialized in `main.py`, so that rate limiting is applied consistently across all routers.

#### Acceptance Criteria

1. THE Rate_Limiter SHALL ser instanciado em `api/main.py` com a função de chave configurada para extrair o Client_IP.
2. THE Rate_Limiter SHALL usar o header `X-Forwarded-For` como fonte primária do Client_IP.
3. WHEN o header `X-Forwarded-For` não estiver presente, THE Rate_Limiter SHALL usar o IP da conexão direta (`request.client.host`) como fallback.
4. WHEN o header `X-Forwarded-For` contiver múltiplos IPs (cadeia de proxies), THE Rate_Limiter SHALL usar o primeiro IP da lista como Client_IP.
5. THE `SlowAPIMiddleware` SHALL ser registrado na aplicação FastAPI via `app.add_middleware`.
6. THE `app.state.limiter` SHALL receber a instância do Rate_Limiter para que o `SlowAPIMiddleware` a encontre.

---

### Requirement 3: Aplicação do Limite nos Endpoints

**User Story:** As an API operator, I want all /v1/ endpoints rate-limited to 60 requests per minute per IP, so that no single client can overload the server.

#### Acceptance Criteria

1. THE Rate_Limiter SHALL aplicar o limite de 60 requisições por minuto por Client_IP em todos os Endpoints sob `/v1/`.
2. THE Rate_Limit_Window SHALL ser de 60 segundos com contagem reiniciada ao fim de cada janela.
3. THE Rate_Limit_Counter SHALL ser mantido em memória, sem dependência de Redis ou banco externo.
4. WHEN um Client_IP realiza até 60 requisições dentro da Rate_Limit_Window, THE API SHALL processar todas as requisições normalmente.
5. WHEN um Client_IP realiza a 61ª requisição dentro da mesma Rate_Limit_Window, THE API SHALL rejeitar a requisição com HTTP 429.

---

### Requirement 4: Resposta de Erro 429

**User Story:** As an API consumer, I want a clear error response when rate limited, so that I can understand why my request was rejected and when to retry.

#### Acceptance Criteria

1. WHEN o limite de requisições é excedido, THE API SHALL retornar HTTP status code 429.
2. WHEN o limite de requisições é excedido, THE API SHALL retornar um corpo JSON com o campo `error` contendo a mensagem `"Rate limit exceeded: 60 per 1 minute"`.
3. WHEN o limite de requisições é excedido, THE API SHALL retornar o header `Retry-After` indicando o número de segundos até o fim da Rate_Limit_Window atual.
4. THE API SHALL registrar um handler de exceção para `RateLimitExceeded` do `slowapi` que produza a resposta descrita nos critérios 1, 2 e 3.

---

### Requirement 5: Compatibilidade com Nginx e X-Forwarded-For

**User Story:** As an infrastructure engineer, I want the API to correctly identify client IPs behind Nginx, so that rate limits are applied per real client and not per proxy IP.

#### Acceptance Criteria

1. WHEN o Nginx encaminha uma requisição com o header `X-Forwarded-For: <client_ip>`, THE Rate_Limiter SHALL usar `<client_ip>` como chave do Rate_Limit_Counter.
2. WHEN o Nginx encaminha uma requisição com o header `X-Forwarded-For: <client_ip>, <proxy_ip>`, THE Rate_Limiter SHALL usar `<client_ip>` (primeiro valor) como chave do Rate_Limit_Counter.
3. WHEN duas requisições chegam com o mesmo `X-Forwarded-For`, THE Rate_Limiter SHALL incrementar o mesmo Rate_Limit_Counter.
4. WHEN duas requisições chegam com `X-Forwarded-For` distintos, THE Rate_Limiter SHALL manter Rate_Limit_Counters independentes para cada Client_IP.

---

### Requirement 6: Endpoints Excluídos do Rate Limiting

**User Story:** As an infrastructure engineer, I want health check and root endpoints excluded from rate limiting, so that monitoring tools are never blocked.

#### Acceptance Criteria

1. THE API SHALL processar requisições para `GET /` sem aplicar Rate_Limit_Counter.
2. THE API SHALL processar requisições para `GET /health` sem aplicar Rate_Limit_Counter.

---

### Requirement 7: Testes de Rate Limiting

**User Story:** As a developer, I want automated tests for the rate limiting behavior, so that regressions are caught before deployment.

#### Acceptance Criteria

1. THE test suite SHALL verificar que a 60ª requisição de um Client_IP dentro da Rate_Limit_Window retorna HTTP 200.
2. THE test suite SHALL verificar que a 61ª requisição do mesmo Client_IP dentro da Rate_Limit_Window retorna HTTP 429.
3. THE test suite SHALL verificar que o corpo da resposta 429 contém o campo `error` com a mensagem `"Rate limit exceeded: 60 per 1 minute"`.
4. THE test suite SHALL verificar que requisições de Client_IPs distintos mantêm contadores independentes.
5. THE test suite SHALL usar o header `X-Forwarded-For` para simular Client_IPs distintos nas requisições de teste.
