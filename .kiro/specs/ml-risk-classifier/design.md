# Design Document

## ml-risk-classifier

---

## Overview

O módulo `ml-risk-classifier` adiciona um pipeline de machine learning ao projeto Astraea para classificar o risco de asteroides. O modelo aprende as regras de negócio já codificadas na coluna `risk_label_rules` (derivada de `mart.mart_asteroids`) e produz duas saídas por asteroide: `risk_label_ml` (classe predita) e `risk_score_ml` (probabilidade da classe `'alto'`). Os resultados são gravados diretamente em `mart.mart_asteroids` via UPDATE SQL.

O pipeline é composto por três scripts Python independentes dentro de `ml/`:

- `train.py` — treina e serializa o modelo
- `predict.py` — carrega o modelo e executa scoring em batch
- `schedule.py` — expõe `run_scoring()` para integração com o APScheduler do collector

---

## Architecture

```mermaid
flowchart TD
    subgraph PostgreSQL
        A[(mart.mart_asteroids)]
    end

    subgraph ml/
        B[train.py]
        C[predict.py]
        D[schedule.py]
        E[models/risk_classifier.joblib]
    end

    subgraph collector/
        F[main.py + APScheduler]
    end

    A -->|SELECT features + target| B
    B -->|joblib.dump| E
    E -->|joblib.load| C
    A -->|SELECT features| C
    C -->|UPDATE risk_score_ml, risk_label_ml| A
    D -->|import + call| C
    F -->|run_scoring\(\)| D

    G[.env na raiz] -->|DATABASE_URL| B
    G -->|DATABASE_URL| C
```

O fluxo de dados é unidirecional: `mart.mart_asteroids` alimenta o treino, o modelo serializado alimenta o scoring, e o scoring escreve de volta na mesma tabela. Não há dependência circular — o scorer lê as features originais, não as colunas ML.

---

## Components and Interfaces

### `ml/train.py`

Responsabilidades:
- Carregar `DATABASE_URL` do `.env` na raiz do projeto (pasta pai de `ml/`)
- Consultar `mart.mart_asteroids` e extrair o Feature_Set e o Target
- Pré-processar `is_potentially_hazardous` (bool → int)
- Treinar `RandomForestClassifier` com hiperparâmetros fixos
- Imprimir métricas para stdout
- Serializar o modelo em `ml/models/risk_classifier.joblib`

Interface pública (linha de comando):
```
python ml/train.py
```

Saída esperada no stdout:
```
Accuracy: 0.XXXX
Classification Report:
              precision    recall  f1-score ...
Feature importances:
  miss_distance_lunar: 0.XX
  ...
[WARNING] Accuracy 0.XX below threshold 0.85   # apenas se accuracy < 0.85
Model saved to ml/models/risk_classifier.joblib
```

### `ml/predict.py`

Responsabilidades:
- Carregar `DATABASE_URL` do `.env` na raiz
- Carregar o modelo de `ml/models/risk_classifier.joblib`
- Consultar `mart.mart_asteroids` e extrair o Feature_Set
- Gerar `risk_score_ml` (probabilidade da classe `'alto'`) e `risk_label_ml` (classe predita)
- Garantir que as colunas existam na tabela via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
- Executar UPDATE em batch por `neo_id`
- Logar o total de registros atualizados

Interface pública (linha de comando):
```
python ml/predict.py
```

Interface pública (importação):
```python
from predict import run_scoring
run_scoring()
```

### `ml/schedule.py`

Responsabilidades:
- Expor `run_scoring()` sem argumentos obrigatórios
- Delegar para a lógica de `predict.py` via import (não subprocess)
- Capturar e logar exceções sem propagar (deixa o caller decidir)

Interface pública:
```python
from ml.schedule import run_scoring
run_scoring()  # chamado pelo APScheduler do collector
```

### `ml/models/`

Diretório de artefatos. Contém `risk_classifier.joblib` após o primeiro treino. Ignorado pelo git (já configurado em `.gitignore`).

### `ml/requirements.txt`

Dependências pinadas para reprodutibilidade:
```
scikit-learn==1.5.2
pandas==2.2.2
sqlalchemy==2.0.30
psycopg2-binary==2.9.9
python-dotenv==1.0.1
joblib==1.4.2
numpy==1.26.4
```

---

## Data Models

### Feature Set (entrada do modelo)

| Coluna | Tipo Python | Origem em `mart.mart_asteroids` | Transformação |
|---|---|---|---|
| `miss_distance_lunar` | float64 | `miss_distance_lunar` | nenhuma |
| `velocity_km_per_s` | float64 | `relative_velocity_km_s` (alias no mart) | nenhuma |
| `diameter_avg_m` | float64 | média de `estimated_diameter_min_km` e `estimated_diameter_max_km` × 1000 | nenhuma (calculado no mart) |
| `absolute_magnitude_h` | float64 | `absolute_magnitude_h` | nenhuma |
| `is_potentially_hazardous` | int64 | `is_potentially_hazardous` (bool) | True → 1, False → 0 |

> Nota: as colunas `velocity_km_per_s` e `diameter_avg_m` são aliases/colunas derivadas presentes em `mart.mart_asteroids`. O script consulta os nomes exatos conforme o mart.

### Target

| Coluna | Tipo | Valores válidos |
|---|---|---|
| `risk_label_rules` | str | `'alto'`, `'médio'`, `'baixo'` |

### Saídas escritas no banco

| Coluna | Tipo SQL | Descrição |
|---|---|---|
| `risk_score_ml` | `NUMERIC(6,4)` | Probabilidade da classe `'alto'` (0.0000–1.0000) |
| `risk_label_ml` | `VARCHAR(10)` | Classe predita pelo modelo |

### Modelo serializado

```
ml/models/risk_classifier.joblib
```

Conteúdo: instância de `sklearn.ensemble.RandomForestClassifier` já treinada. Carregada via `joblib.load()` no scorer.

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Boolean cast preserva apenas 0 e 1

*For any* DataFrame com a coluna `is_potentially_hazardous` contendo valores booleanos, após a transformação de pré-processamento, todos os valores da coluna devem ser exatamente 0 ou 1 (inteiros), sem valores nulos ou outros.

**Validates: Requirements 2.5**

---

### Property 2: Proporções do split treino/teste

*For any* dataset com pelo menos 10 amostras por classe, ao aplicar o split 80/20 com `stratify=y`, o conjunto de teste deve conter entre 19% e 21% das amostras totais, e a distribuição de classes no teste deve refletir a distribuição original dentro de uma margem de 5%.

**Validates: Requirements 3.2**

---

### Property 3: risk_score_ml está no intervalo [0, 1]

*For any* conjunto de linhas de `mart.mart_asteroids` com o Feature_Set completo e sem nulos, todos os valores de `risk_score_ml` gerados pelo scorer devem ser floats no intervalo fechado [0.0, 1.0].

**Validates: Requirements 5.4**

---

### Property 4: risk_label_ml pertence ao conjunto de classes válidas

*For any* conjunto de linhas de `mart.mart_asteroids` com o Feature_Set completo, todos os valores de `risk_label_ml` gerados pelo scorer devem ser exatamente um dos valores `'alto'`, `'médio'` ou `'baixo'`.

**Validates: Requirements 5.5**

---

### Property 5: Round-trip de escrita — predições persistidas são recuperáveis

*For any* conjunto de predições geradas pelo scorer, após executar os UPDATEs, uma consulta `SELECT neo_id, risk_score_ml, risk_label_ml FROM mart.mart_asteroids WHERE neo_id = :id` deve retornar os mesmos valores que foram escritos para cada `neo_id`.

**Validates: Requirements 6.3**

---

### Property 6: Ranking ML captura todos os asteroides de alto risco

*For any* execução completa do scorer sobre `mart.mart_asteroids`, os 10 registros com maior `risk_score_ml` devem incluir todos os registros onde `risk_label_rules = 'alto'` (assumindo que o número de asteroides 'alto' é ≤ 10).

**Validates: Requirements 8.1**

---

## Error Handling

| Situação | Componente | Comportamento |
|---|---|---|
| `DATABASE_URL` não definida | `train.py`, `predict.py` | Raise `EnvironmentError` com mensagem descritiva; exit code 1 |
| `ml/models/risk_classifier.joblib` não encontrado | `predict.py` | Raise `FileNotFoundError` com mensagem descritiva; exit code 1 |
| `ml/models/` não existe | `train.py` | `os.makedirs(..., exist_ok=True)` antes de salvar |
| Exceção em `run_scoring()` | `schedule.py` | Captura, loga via `logging.exception()`, não propaga |
| Colunas ML ausentes na tabela | `predict.py` | `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` garante idempotência |
| Dados nulos no Feature_Set | `predict.py` | Logar aviso e pular linhas com nulos (ou imputar com mediana — decisão de implementação) |

---

## Testing Strategy

### Abordagem dual

O módulo usa dois tipos complementares de teste:

- **Testes unitários/exemplos**: verificam comportamentos específicos, casos de borda e condições de erro com dados fixos
- **Testes de propriedade (PBT)**: verificam invariantes universais com dados gerados aleatoriamente

### Biblioteca de PBT

Usar **[Hypothesis](https://hypothesis.readthedocs.io/)** (Python). Cada teste de propriedade deve rodar com mínimo de 100 iterações (padrão do Hypothesis com `@settings(max_examples=100)`).

### Testes unitários (exemplos e casos de borda)

- `test_requirements_txt_versions` — verifica que cada pacote aparece com a versão exata pinada (Req 1.2)
- `test_dotenv_path_resolution` — verifica que o `.env` é carregado do diretório pai de `ml/` (Req 2.1)
- `test_missing_database_url_raises` — sem `DATABASE_URL`, deve levantar `EnvironmentError` (Req 2.2)
- `test_trainer_queries_correct_table` — mock DB, verifica que a query acessa `mart.mart_asteroids` (Req 2.3)
- `test_feature_columns_selected` — verifica que o DataFrame resultante tem exatamente as 5 colunas do Feature_Set (Req 2.4)
- `test_target_column_is_risk_label_rules` — verifica que `y` é extraído de `risk_label_rules` (Req 2.6)
- `test_model_hyperparameters` — inspeciona `model.get_params()` após treino (Req 3.1)
- `test_stdout_contains_metrics` — captura stdout e verifica presença de "Accuracy", "Classification Report", "Feature importances" (Req 3.3)
- `test_low_accuracy_warning` — mock de accuracy < 0.85, verifica warning no stdout (Req 3.4)
- `test_model_saved_to_correct_path` — verifica que o arquivo existe após `train.py` (Req 4.1)
- `test_models_dir_created_if_missing` — remove o diretório e verifica que é recriado (Req 4.2)
- `test_gitignore_contains_joblib_pattern` — lê `.gitignore` e verifica o padrão (Req 4.3)
- `test_scorer_loads_model_from_correct_path` — mock `joblib.load`, verifica o caminho (Req 5.1)
- `test_missing_model_file_raises` — sem o `.joblib`, deve levantar `FileNotFoundError` (Req 5.2)
- `test_alter_table_statements_issued` — mock connection, verifica os dois ALTER TABLE (Req 6.1, 6.2)
- `test_update_count_logged` — captura stdout, verifica que o número de registros é logado (Req 6.4)
- `test_run_scoring_is_callable` — importa `schedule.py` e verifica que `run_scoring` é callable sem args (Req 7.1)
- `test_run_scoring_no_subprocess` — mock `subprocess`, verifica que nunca é chamado (Req 7.2)
- `test_run_scoring_logs_exception` — mock scorer para raise, verifica log de erro (Req 7.3)
- `test_model_accuracy_threshold` — treina com dados reais e verifica accuracy >= 0.85 (Req 8.2)

### Testes de propriedade (Hypothesis)

Cada teste deve incluir o comentário de tag no formato:
`# Feature: ml-risk-classifier, Property N: <texto da propriedade>`

```python
# Feature: ml-risk-classifier, Property 1: Boolean cast preserva apenas 0 e 1
@given(st.lists(st.booleans(), min_size=1))
@settings(max_examples=100)
def test_bool_cast_property(bool_values): ...

# Feature: ml-risk-classifier, Property 2: Proporções do split treino/teste
@given(dataframes com distribuição de classes variada)
@settings(max_examples=100)
def test_split_proportions_property(df): ...

# Feature: ml-risk-classifier, Property 3: risk_score_ml está no intervalo [0, 1]
@given(feature_rows geradas aleatoriamente)
@settings(max_examples=100)
def test_risk_score_range_property(rows): ...

# Feature: ml-risk-classifier, Property 4: risk_label_ml pertence ao conjunto de classes válidas
@given(feature_rows geradas aleatoriamente)
@settings(max_examples=100)
def test_risk_label_valid_values_property(rows): ...

# Feature: ml-risk-classifier, Property 5: Round-trip de escrita
@given(conjuntos de predições geradas aleatoriamente)
@settings(max_examples=100)
def test_write_roundtrip_property(predictions): ...

# Feature: ml-risk-classifier, Property 6: Ranking ML captura todos os asteroides de alto risco
@given(datasets com subconjunto de asteroides 'alto')
@settings(max_examples=100)
def test_ranking_captures_high_risk_property(dataset): ...
```

> Nota: os testes de propriedade 3, 4 e 6 requerem um modelo treinado como fixture. Usar um modelo treinado em dados sintéticos para os testes unitários, e o modelo real apenas no teste de integração (Req 8.2).
