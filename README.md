# 🌌 Astraea

**Plataforma de monitoramento de objetos próximos à Terra e eventos solares**, alimentada pela API da NASA e com classificação de risco via Machine Learning.

---

## Visão Geral

O Astraea coleta dados em tempo real da NASA, transforma e enriquece essas informações com dbt, classifica o risco de asteroides com um modelo de Random Forest e expõe tudo via uma API REST — com um dashboard web para visualização.

```
NASA APIs (NeoWs + DONKI)
        │
        ▼
  [Collector] ──► PostgreSQL (raw)
                        │
                        ▼
                   [dbt] ──► staging / mart
                        │
              ┌─────────┴──────────┐
              ▼                    ▼
          [ML Model]           [FastAPI]
        (risk scoring)             │
              │                    ▼
              └──────────► [Dashboard Web]
```

---

## Componentes

| Componente | Tecnologia | Descrição |
|---|---|---|
| `collector/` | Python + APScheduler | Coleta diária de asteroides (NeoWs) e eventos solares (DONKI/CME, DONKI/GST) |
| `dbt/astraea/` | dbt Core + PostgreSQL | Transformação dos dados raw → staging → mart com score de risco |
| `ml/` | scikit-learn + joblib | Treinamento e scoring batch de classificador de risco (Random Forest) |
| `api/` | FastAPI | API REST com endpoints de asteroides, eventos solares e estatísticas |
| `dashboard/` | HTML/CSS/JS | Interface web para visualização dos dados |
| `scripts/` | SQL | Inicialização idempotente do banco de dados |

---

## Pré-requisitos

- [Docker](https://www.docker.com/) e Docker Compose
- Python 3.11+
- [dbt Core](https://docs.getdbt.com/docs/core/installation) (para rodar transformações localmente)
- Chave de API da NASA — obtenha gratuitamente em [api.nasa.gov](https://api.nasa.gov/)

---

## Configuração

1. Clone o repositório:

```bash
git clone https://github.com/alexarnoni/astraea.git
cd astraea
```

2. Copie o arquivo de variáveis de ambiente e preencha:

```bash
cp .env.example .env
```

```env
POSTGRES_USER=astraea
POSTGRES_PASSWORD=sua_senha_aqui
POSTGRES_DB=astraea
DATABASE_URL=postgresql://astraea:sua_senha_aqui@db:5432/astraea
NASA_API_KEY=sua_chave_aqui
```

---

## Como Rodar

### Subir tudo com Docker Compose

```bash
docker-compose up --build
```

Isso sobe o PostgreSQL, o collector (com coleta imediata + agendamento diário) e a API.

### Rodar as transformações dbt

```bash
cd dbt/astraea
dbt run
dbt test
```

### Treinar o modelo de ML

```bash
python ml/train.py
```

### Executar scoring batch

```bash
python ml/predict.py
```

---

## API

A API estará disponível em `http://localhost:8000`. Documentação interativa em `http://localhost:8000/docs`.

### Endpoints principais

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/v1/asteroids` | Lista asteroides com filtros (data, risco, hazardous) |
| `GET` | `/v1/asteroids/upcoming` | Próximas aproximações (a partir de hoje) |
| `GET` | `/v1/asteroids/{neo_id}` | Detalhes de um asteroide específico |
| `GET` | `/v1/solar-events` | Lista eventos solares (CME, GST) com filtros |
| `GET` | `/v1/solar-events/earth-directed` | CMEs registrados |
| `GET` | `/v1/stats/summary` | Resumo estatístico geral |

### Exemplo de resposta — `/v1/stats/summary`

```json
{
  "total_asteroids": 1420,
  "hazardous_count": 312,
  "high_risk_ml": 87,
  "medium_risk_ml": 445,
  "low_risk_ml": 888,
  "total_solar_events": 203,
  "cme_count": 178,
  "gst_count": 25,
  "closest_approach_lunar": 1.23,
  "closest_asteroid_name": "(2024 BX1)"
}
```

---

## Modelo de Risco (ML)

O classificador usa **Random Forest** treinado sobre dados históricos do mart, com as seguintes features:

| Feature | Descrição |
|---|---|
| `miss_distance_lunar` | Distância de passagem em unidades lunares |
| `relative_velocity_km_s` | Velocidade relativa em km/s |
| `diameter_avg_km` | Diâmetro médio estimado em km |
| `absolute_magnitude_h` | Magnitude absoluta |
| `is_potentially_hazardous` | Flag NASA de objeto potencialmente perigoso |

**Labels de saída:** `baixo` · `médio` · `alto`

O modelo é serializado em `ml/models/risk_classifier.joblib` e aplicado em batch via `ml/predict.py`, que atualiza as colunas `risk_score_ml` e `risk_label_ml` diretamente no mart.

---

## Estrutura do Banco de Dados

```
raw.neo_feeds          — dados brutos de asteroides (JSONB)
raw.solar_events       — dados brutos de eventos solares (JSONB)
staging.stg_asteroids  — asteroides normalizados
staging.stg_solar_events — eventos solares normalizados
mart.mart_asteroids    — asteroides enriquecidos com score de risco
mart.mart_solar_events — eventos solares enriquecidos
```

---

## Testes

```bash
# Dashboard (Vitest)
cd dashboard
npm test

# ML
cd ml
pytest tests/
```

---

## Fontes de Dados

- [NASA NeoWs](https://api.nasa.gov/neo/rest/v1/feed) — Near Earth Object Web Service
- [NASA DONKI](https://api.nasa.gov/DONKI/) — Space Weather Database Of Notifications, Knowledge, Information

---

## Licença

MIT
