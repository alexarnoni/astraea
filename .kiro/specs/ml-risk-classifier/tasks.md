# Implementation Plan: ml-risk-classifier

## Overview

Pipeline de ML em Python para classificação de risco de asteroides. Os scripts são independentes e residem em `ml/`. O treino lê de `mart.mart_asteroids`, serializa o modelo em `ml/models/`, e o scorer escreve `risk_score_ml` e `risk_label_ml` de volta na mesma tabela. O `schedule.py` expõe `run_scoring()` para o APScheduler do collector.

## Tasks

- [x] 1. Criar `ml/requirements.txt` com dependências pinadas
  - Declarar exatamente: `scikit-learn==1.5.2`, `pandas==2.2.2`, `sqlalchemy==2.0.30`, `psycopg2-binary==2.9.9`, `python-dotenv==1.0.1`, `joblib==1.4.2`, `numpy==1.26.4`
  - _Requirements: 1.1, 1.2_

  - [ ]* 1.1 Escrever teste unitário `test_requirements_txt_versions`
    - Ler `ml/requirements.txt` e verificar que cada pacote aparece com a versão exata pinada
    - _Requirements: 1.2_

- [x] 2. Criar `ml/train.py` — carregamento de dados e pré-processamento
  - Carregar `DATABASE_URL` do `.env` na raiz do projeto (pasta pai de `ml/`) via `python-dotenv`
  - Levantar `EnvironmentError` descritivo quando `DATABASE_URL` não estiver definida
  - Consultar todos os registros de `mart.mart_asteroids` via SQLAlchemy
  - Selecionar exatamente as 5 colunas do Feature_Set: `miss_distance_lunar`, `velocity_km_per_s`, `diameter_avg_m`, `absolute_magnitude_h`, `is_potentially_hazardous`
  - Extrair `risk_label_rules` como Target
  - Converter `is_potentially_hazardous` de bool para int (True → 1, False → 0)
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ]* 2.1 Escrever teste unitário `test_dotenv_path_resolution`
    - Verificar que o `.env` é carregado do diretório pai de `ml/`
    - _Requirements: 2.1_

  - [ ]* 2.2 Escrever teste unitário `test_missing_database_url_raises`
    - Sem `DATABASE_URL`, deve levantar `EnvironmentError`
    - _Requirements: 2.2_

  - [ ]* 2.3 Escrever teste unitário `test_trainer_queries_correct_table`
    - Mock DB, verificar que a query acessa `mart.mart_asteroids`
    - _Requirements: 2.3_

  - [ ]* 2.4 Escrever teste unitário `test_feature_columns_selected`
    - Verificar que o DataFrame resultante tem exatamente as 5 colunas do Feature_Set
    - _Requirements: 2.4_

  - [ ]* 2.5 Escrever teste unitário `test_target_column_is_risk_label_rules`
    - Verificar que `y` é extraído de `risk_label_rules`
    - _Requirements: 2.6_

  - [ ]* 2.6 Escrever property test para pré-processamento booleano
    - **Property 1: Boolean cast preserva apenas 0 e 1**
    - `@given(st.lists(st.booleans(), min_size=1))` — após cast, todos os valores devem ser exatamente 0 ou 1, sem nulos
    - **Validates: Requirements 2.5**

- [x] 3. Implementar treino, métricas e persistência em `ml/train.py`
  - Treinar `RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')`
  - Split 80/20 com `stratify=y, random_state=42`
  - Imprimir accuracy, classification report e feature importances para stdout
  - Imprimir warning quando accuracy < 0.85
  - Criar `ml/models/` com `os.makedirs(..., exist_ok=True)` se não existir
  - Serializar modelo em `ml/models/risk_classifier.joblib` via `joblib.dump`
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.1, 4.2_

  - [ ]* 3.1 Escrever property test para proporções do split
    - **Property 2: Proporções do split treino/teste**
    - `@given(datasets com distribuição de classes variada, min 10 amostras por classe)` — conjunto de teste deve conter entre 19% e 21% das amostras; distribuição de classes no teste deve refletir a original dentro de 5%
    - **Validates: Requirements 3.2**

  - [ ]* 3.2 Escrever teste unitário `test_model_hyperparameters`
    - Inspecionar `model.get_params()` após treino e verificar `n_estimators=100`, `random_state=42`, `class_weight='balanced'`
    - _Requirements: 3.1_

  - [ ]* 3.3 Escrever teste unitário `test_stdout_contains_metrics`
    - Capturar stdout e verificar presença de "Accuracy", "Classification Report", "Feature importances"
    - _Requirements: 3.3_

  - [ ]* 3.4 Escrever teste unitário `test_low_accuracy_warning`
    - Mock de accuracy < 0.85, verificar warning no stdout
    - _Requirements: 3.4_

  - [ ]* 3.5 Escrever teste unitário `test_model_saved_to_correct_path`
    - Verificar que `ml/models/risk_classifier.joblib` existe após execução do trainer
    - _Requirements: 4.1_

  - [ ]* 3.6 Escrever teste unitário `test_models_dir_created_if_missing`
    - Remover o diretório e verificar que é recriado automaticamente
    - _Requirements: 4.2_

- [x] 4. Garantir `ml/models/*.joblib` no `.gitignore`
  - Verificar se o padrão `ml/models/*.joblib` já está presente no `.gitignore` raiz; adicionar se ausente
  - _Requirements: 4.3_

  - [ ]* 4.1 Escrever teste unitário `test_gitignore_contains_joblib_pattern`
    - Ler `.gitignore` e verificar que o padrão `ml/models/*.joblib` está presente
    - _Requirements: 4.3_

- [x] 5. Criar `ml/predict.py` — carregamento do modelo e scoring batch
  - Carregar `DATABASE_URL` do `.env` na raiz (mesmo padrão do trainer)
  - Levantar `FileNotFoundError` descritivo quando `ml/models/risk_classifier.joblib` não existir
  - Carregar modelo via `joblib.load('ml/models/risk_classifier.joblib')`
  - Consultar todos os registros de `mart.mart_asteroids` e extrair o Feature_Set
  - Converter `is_potentially_hazardous` bool → int
  - Gerar `risk_score_ml` como `predict_proba` da classe `'alto'` (float [0,1])
  - Gerar `risk_label_ml` como `predict` (classe predita)
  - Executar `ALTER TABLE mart.mart_asteroids ADD COLUMN IF NOT EXISTS risk_score_ml NUMERIC(6,4)` antes de escrever
  - Executar `ALTER TABLE mart.mart_asteroids ADD COLUMN IF NOT EXISTS risk_label_ml VARCHAR(10)` antes de escrever
  - Executar UPDATE em batch por `neo_id` para cada linha
  - Logar total de registros atualizados para stdout
  - Expor `run_scoring()` como função importável sem argumentos obrigatórios
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4_

  - [ ]* 5.1 Escrever teste unitário `test_scorer_loads_model_from_correct_path`
    - Mock `joblib.load`, verificar que o caminho `ml/models/risk_classifier.joblib` é usado
    - _Requirements: 5.1_

  - [ ]* 5.2 Escrever teste unitário `test_missing_model_file_raises`
    - Sem o `.joblib`, deve levantar `FileNotFoundError`
    - _Requirements: 5.2_

  - [ ]* 5.3 Escrever teste unitário `test_alter_table_statements_issued`
    - Mock connection, verificar que os dois ALTER TABLE são executados antes dos UPDATEs
    - _Requirements: 6.1, 6.2_

  - [ ]* 5.4 Escrever teste unitário `test_update_count_logged`
    - Capturar stdout e verificar que o número de registros atualizados é logado
    - _Requirements: 6.4_

  - [ ]* 5.5 Escrever property test para intervalo de `risk_score_ml`
    - **Property 3: risk_score_ml está no intervalo [0, 1]**
    - `@given(feature_rows geradas aleatoriamente com modelo treinado em dados sintéticos)` — todos os valores de `risk_score_ml` devem ser floats em [0.0, 1.0]
    - **Validates: Requirements 5.4**

  - [ ]* 5.6 Escrever property test para valores válidos de `risk_label_ml`
    - **Property 4: risk_label_ml pertence ao conjunto de classes válidas**
    - `@given(feature_rows geradas aleatoriamente)` — todos os valores de `risk_label_ml` devem ser exatamente `'alto'`, `'médio'` ou `'baixo'`
    - **Validates: Requirements 5.5**

  - [ ]* 5.7 Escrever property test para round-trip de escrita
    - **Property 5: Round-trip de escrita — predições persistidas são recuperáveis**
    - `@given(conjuntos de predições geradas aleatoriamente)` — após UPDATEs, SELECT por `neo_id` deve retornar os mesmos valores escritos
    - **Validates: Requirements 6.3**

  - [ ]* 5.8 Escrever property test para ranking de alto risco
    - **Property 6: Ranking ML captura todos os asteroides de alto risco**
    - `@given(datasets onde número de asteroides 'alto' ≤ 10)` — os 10 registros com maior `risk_score_ml` devem incluir todos os registros onde `risk_label_rules = 'alto'`
    - **Validates: Requirements 8.1**

- [x] 6. Checkpoint — verificar integração trainer → scorer
  - Garantir que `train.py` gera o `.joblib` e `predict.py` consegue carregá-lo sem erros
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Criar `ml/schedule.py` — wrapper para o APScheduler
  - Importar e chamar `run_scoring` de `predict.py` (não subprocess)
  - Expor `run_scoring()` sem argumentos obrigatórios
  - Capturar qualquer exceção, logar via `logging.exception()` e não propagar
  - _Requirements: 7.1, 7.2, 7.3_

  - [ ]* 7.1 Escrever teste unitário `test_run_scoring_is_callable`
    - Importar `schedule.py` e verificar que `run_scoring` é callable sem argumentos
    - _Requirements: 7.1_

  - [ ]* 7.2 Escrever teste unitário `test_run_scoring_no_subprocess`
    - Mock `subprocess`, verificar que nunca é chamado durante `run_scoring()`
    - _Requirements: 7.2_

  - [ ]* 7.3 Escrever teste unitário `test_run_scoring_logs_exception`
    - Mock scorer para levantar exceção, verificar que o erro é logado e não propagado
    - _Requirements: 7.3_

- [ ] 8. Teste de integração de qualidade do modelo
  - [ ]* 8.1 Escrever teste de integração `test_model_accuracy_threshold`
    - Treinar com dados reais de `mart.mart_asteroids` e verificar accuracy >= 0.85 no split de teste
    - _Requirements: 8.2_

- [x] 9. Checkpoint final — garantir que todos os testes passam
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marcadas com `*` são opcionais e podem ser puladas para um MVP mais rápido
- Cada task referencia os requisitos específicos para rastreabilidade
- Os testes de propriedade 3, 4 e 6 requerem um modelo treinado como fixture — usar modelo treinado em dados sintéticos para testes unitários, modelo real apenas no teste de integração (task 8.1)
- O `.env` já está no `.gitignore`; `ml/models/*.joblib` já está coberto — verificar na task 4
- Todos os scripts devem ser executáveis a partir da raiz do projeto: `python ml/train.py`, `python ml/predict.py`
