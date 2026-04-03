# Requirements Document

## Introduction

O módulo `ml-risk-classifier` adiciona ao projeto Astraea um pipeline de machine learning para classificação de risco de asteroides. O modelo aprende as regras de negócio já codificadas em `risk_label_rules` (alto/médio/baixo) e produz duas saídas por asteroide: `risk_label_ml` (classe predita) e `risk_score_ml` (probabilidade da classe 'alto'). Os resultados são gravados diretamente em `mart.mart_asteroids` e o pipeline de scoring pode ser acionado pelo scheduler do collector após cada coleta diária.

## Glossary

- **Trainer**: script `ml/train.py` responsável por treinar e serializar o modelo
- **Scorer**: script `ml/predict.py` responsável por carregar o modelo e gerar predições em batch
- **Scheduler_Wrapper**: módulo `ml/schedule.py` que expõe `run_scoring()` para integração com o APScheduler do collector
- **Model_Store**: diretório `ml/models/` onde artefatos `.joblib` são persistidos
- **Mart**: schema `mart` no PostgreSQL, especificamente a tabela `mart.mart_asteroids`
- **Feature_Set**: conjunto de colunas usadas como entrada do modelo — `miss_distance_lunar`, `velocity_km_per_s`, `diameter_avg_m`, `absolute_magnitude_h`, `is_potentially_hazardous`
- **Target**: coluna `risk_label_rules` com valores `'alto'`, `'médio'` ou `'baixo'`
- **DATABASE_URL**: variável de ambiente com a connection string PostgreSQL, carregada do `.env` na raiz do projeto

---

## Requirements

### Requirement 1: Instalação de Dependências

**User Story:** As a data scientist, I want a pinned `requirements.txt` for the ML module, so that the environment is reproducible across machines.

#### Acceptance Criteria

1. THE Trainer SHALL be executable after running `pip install -r ml/requirements.txt` without additional manual steps.
2. THE `ml/requirements.txt` SHALL declare exact versions for: `scikit-learn==1.5.2`, `pandas==2.2.2`, `sqlalchemy==2.0.30`, `psycopg2-binary==2.9.9`, `python-dotenv==1.0.1`, `joblib==1.4.2`, `numpy==1.26.4`.

---

### Requirement 2: Carregamento de Dados de Treino

**User Story:** As a data scientist, I want the Trainer to load data from the Mart, so that the model is trained on the same data used by the pipeline.

#### Acceptance Criteria

1. WHEN the Trainer is executed, THE Trainer SHALL load `DATABASE_URL` from the `.env` file located one directory above `ml/`.
2. WHEN `DATABASE_URL` is not set, THEN THE Trainer SHALL raise a descriptive error and exit with a non-zero status code.
3. WHEN the Trainer connects to the database, THE Trainer SHALL query all rows from `mart.mart_asteroids`.
4. THE Trainer SHALL select exactly the following columns as the Feature_Set: `miss_distance_lunar`, `velocity_km_per_s`, `diameter_avg_m`, `absolute_magnitude_h`, `is_potentially_hazardous`.
5. THE Trainer SHALL cast `is_potentially_hazardous` to integer (True → 1, False → 0) before training.
6. THE Trainer SHALL use `risk_label_rules` as the Target column.

---

### Requirement 3: Treinamento do Modelo

**User Story:** As a data scientist, I want a RandomForest trained with reproducible settings, so that results are consistent and class imbalance is handled.

#### Acceptance Criteria

1. THE Trainer SHALL train a `RandomForestClassifier` with `n_estimators=100`, `random_state=42`, and `class_weight='balanced'`.
2. THE Trainer SHALL split data into train (80%) and test (20%) sets using `stratify=y` and `random_state=42`.
3. WHEN training completes, THE Trainer SHALL print accuracy, a full classification report, and feature importances to stdout.
4. WHEN the test set accuracy is below 0.85, THE Trainer SHALL print a warning message indicating the accuracy threshold was not met.

---

### Requirement 4: Persistência do Modelo

**User Story:** As a data scientist, I want the trained model saved to disk, so that the Scorer can load it without retraining.

#### Acceptance Criteria

1. WHEN training completes successfully, THE Trainer SHALL serialize the model to `ml/models/risk_classifier.joblib` using `joblib.dump`.
2. WHEN `ml/models/` does not exist, THE Trainer SHALL create the directory before saving.
3. THE Model_Store path `ml/models/*.joblib` SHALL be listed in `.gitignore` so model artifacts are not committed to version control.

---

### Requirement 5: Scoring em Batch

**User Story:** As a data engineer, I want the Scorer to generate ML predictions for all asteroids, so that the Mart contains up-to-date ML risk scores.

#### Acceptance Criteria

1. WHEN the Scorer is executed, THE Scorer SHALL load the model from `ml/models/risk_classifier.joblib`.
2. WHEN `ml/models/risk_classifier.joblib` does not exist, THEN THE Scorer SHALL raise a descriptive error and exit with a non-zero status code.
3. WHEN the Scorer connects to the database, THE Scorer SHALL load all rows from `mart.mart_asteroids` using `DATABASE_URL`.
4. THE Scorer SHALL generate `risk_score_ml` as the predicted probability of class `'alto'` (float, range 0–1) for each row.
5. THE Scorer SHALL generate `risk_label_ml` as the predicted class label (`'alto'`, `'médio'`, or `'baixo'`) for each row.

---

### Requirement 6: Escrita dos Resultados no Banco

**User Story:** As a data engineer, I want predictions written back to `mart.mart_asteroids`, so that downstream consumers can query ML scores alongside rule-based scores.

#### Acceptance Criteria

1. WHEN the Scorer runs, THE Scorer SHALL execute `ALTER TABLE mart.mart_asteroids ADD COLUMN IF NOT EXISTS risk_score_ml NUMERIC(6,4)` before writing results.
2. WHEN the Scorer runs, THE Scorer SHALL execute `ALTER TABLE mart.mart_asteroids ADD COLUMN IF NOT EXISTS risk_label_ml VARCHAR(10)` before writing results.
3. THE Scorer SHALL update `risk_score_ml` and `risk_label_ml` for each row identified by `neo_id` via a SQL `UPDATE` statement.
4. WHEN all updates complete, THE Scorer SHALL log the total number of records updated to stdout.

---

### Requirement 7: Integração com o Scheduler

**User Story:** As a data engineer, I want a scheduler wrapper that triggers scoring after each daily collection, so that ML scores stay current without manual intervention.

#### Acceptance Criteria

1. THE Scheduler_Wrapper SHALL export a callable `run_scoring()` with no required arguments.
2. WHEN `run_scoring()` is called, THE Scheduler_Wrapper SHALL execute the Scorer logic as a Python module import (not a subprocess).
3. WHEN `run_scoring()` raises an exception, THE Scheduler_Wrapper SHALL log the error and allow the caller to handle it.

---

### Requirement 8: Qualidade das Predições

**User Story:** As a product owner, I want the ML model to correctly rank the highest-risk asteroids, so that the risk scores are actionable.

#### Acceptance Criteria

1. WHEN `predict.py` completes, THE Scorer SHALL produce results such that a query `SELECT ... FROM mart.mart_asteroids ORDER BY risk_score_ml DESC LIMIT 10` includes all rows where `risk_label_rules = 'alto'`.
2. THE Trainer SHALL achieve accuracy >= 0.85 on the 20% test split of `mart.mart_asteroids`.
