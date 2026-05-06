# Requirements Document

## Introduction

Este documento define os requisitos para adicionar metadados de rastreabilidade científica ao pipeline de treinamento e inferência do modelo de ML. Atualmente, `ml/train.py` salva apenas o arquivo `.joblib` sem qualquer informação contextual. Para fins de reprodutibilidade científica (e futura publicação em arXiv), o sistema deve registrar metadados como versão do modelo, data de treinamento, versão do scikit-learn, colunas de features, intervalo dos dados de treino e acurácia. Esses metadados devem ser propagados até a API para que consumidores saibam qual versão do modelo gerou as predições.

## Glossary

- **Training_Pipeline**: O módulo `ml/train.py` responsável por treinar e serializar o classificador de risco de asteroides.
- **Scoring_Pipeline**: O módulo `ml/predict.py` responsável por carregar o modelo treinado e executar predições batch.
- **Metadata_File**: Arquivo JSON (`metadata.json`) salvo no diretório `ml/models/` contendo informações de rastreabilidade do modelo.
- **API_Router**: O módulo `api/routers/asteroids.py` que serve endpoints REST para dados de asteroides.
- **AsteroidResponse**: O modelo Pydantic em `api/models.py` que define o schema de resposta da API.
- **Version_Compatibility_Test**: Teste automatizado que verifica se o modelo serializado é compatível com a versão atual do scikit-learn.

## Requirements

### Requirement 1: Geração de Metadados no Treinamento

**User Story:** As a researcher, I want the training pipeline to save structured metadata alongside the model, so that I can trace exactly how and when the model was produced.

#### Acceptance Criteria

1. WHEN the Training_Pipeline saves a model, THE Training_Pipeline SHALL create a `metadata.json` file in the same directory as the model file.
2. THE Metadata_File SHALL contain the field `model_version` with value `"1.0.0"`.
3. THE Metadata_File SHALL contain the field `trained_at` with the training timestamp in UTC ISO 8601 format.
4. THE Metadata_File SHALL contain the field `sklearn_version` with the version string of the scikit-learn library used during training.
5. THE Metadata_File SHALL contain the field `feature_columns` with the ordered list of feature column names used for training.
6. WHEN a DataFrame with a `feed_date` column is provided, THE Metadata_File SHALL contain the field `training_data_range` as an object with `start` (earliest date) and `end` (latest date) in ISO 8601 format.
7. THE Metadata_File SHALL contain the field `total_samples` with the total number of rows in the training DataFrame.
8. THE Metadata_File SHALL contain the field `accuracy` with the model accuracy score as a float.
9. WHEN the `save_model` function is called, THE Training_Pipeline SHALL accept `df` and `metrics` as parameters in addition to the model.

### Requirement 2: Logging de Metadados na Inferência

**User Story:** As a ML engineer, I want the scoring pipeline to log model version and training date at startup, so that I can verify which model is being used in production.

#### Acceptance Criteria

1. WHEN the Scoring_Pipeline loads the model, THE Scoring_Pipeline SHALL also load the `metadata.json` file from the same directory.
2. WHEN the Metadata_File is loaded successfully, THE Scoring_Pipeline SHALL log the `model_version` value to stdout.
3. WHEN the Metadata_File is loaded successfully, THE Scoring_Pipeline SHALL log the `trained_at` value to stdout.
4. IF the Metadata_File does not exist, THEN THE Scoring_Pipeline SHALL log a warning message and continue execution without interruption.

### Requirement 3: Exposição de Metadados na API

**User Story:** As an API consumer, I want asteroid responses to include model version information, so that I can assess the provenance of risk predictions.

#### Acceptance Criteria

1. THE AsteroidResponse SHALL include an optional field `model_version` of type string with default value `None`.
2. THE AsteroidResponse SHALL include an optional field `model_trained_at` of type string with default value `None`.
3. WHEN the API_Router module is loaded, THE API_Router SHALL load the `metadata.json` file once at module startup.
4. WHEN the API_Router constructs an AsteroidResponse, THE API_Router SHALL inject the `model_version` value from the loaded metadata.
5. WHEN the API_Router constructs an AsteroidResponse, THE API_Router SHALL inject the `model_trained_at` value from the loaded metadata.
6. IF the Metadata_File does not exist at module startup, THEN THE API_Router SHALL set `model_version` and `model_trained_at` to `None` in responses.

### Requirement 4: Teste de Compatibilidade de Versão do Modelo

**User Story:** As a developer, I want an automated test that detects sklearn version mismatches, so that I am alerted before deploying a model trained with an incompatible library version.

#### Acceptance Criteria

1. THE Version_Compatibility_Test SHALL load the serialized model using `warnings.catch_warnings` to capture `InconsistentVersionWarning`.
2. IF an `InconsistentVersionWarning` is detected during model loading, THEN THE Version_Compatibility_Test SHALL fail with a descriptive message indicating the version mismatch.
3. WHEN no `InconsistentVersionWarning` is detected, THE Version_Compatibility_Test SHALL pass successfully.
4. THE Version_Compatibility_Test SHALL be located at `ml/tests/test_model_version.py`.

### Requirement 5: Serialização e Leitura do Metadata (Round-Trip)

**User Story:** As a developer, I want to ensure that metadata written during training can be read back identically, so that no information is lost in the serialization process.

#### Acceptance Criteria

1. FOR ALL valid metadata objects, writing to JSON then reading back SHALL produce an equivalent object (round-trip property).
2. THE Metadata_File SHALL be valid JSON parseable by the standard `json` module.
3. THE Metadata_File SHALL use UTF-8 encoding.
