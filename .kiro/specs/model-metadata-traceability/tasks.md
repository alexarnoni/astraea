# Implementation Plan: Model Metadata Traceability

## Overview

Implementação incremental de metadados de rastreabilidade científica no pipeline de ML. Cada tarefa constrói sobre a anterior, começando pela geração de metadados no treinamento, passando pelo logging na inferência, exposição na API, e finalizando com testes de compatibilidade.

## Tasks

- [x] 1. Implement metadata generation in training pipeline
  - [x] 1.1 Update `save_model` signature and implement `_build_metadata` in `ml/train.py`
    - Add imports: `json`, `datetime` (timezone, datetime), `sklearn`
    - Create `_build_metadata(df: pd.DataFrame, metrics: dict) -> dict` function
    - Update `save_model` signature to accept `df` and `metrics` parameters
    - Write `metadata.json` alongside the model using `json.dump` with `ensure_ascii=False, indent=2` and UTF-8 encoding
    - Update `main()` to pass `df` and `metrics` to `save_model`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9_

  - [ ]* 1.2 Write property test for metadata building (Property 1)
    - **Property 1: Metadata building preserves input-dependent fields**
    - Create `ml/tests/test_metadata_properties.py`
    - Use hypothesis to generate DataFrames with `feed_date` column and metrics dicts with `accuracy` float
    - Assert `training_data_range.start` == min feed_date, `training_data_range.end` == max feed_date, `total_samples` == len(df), `accuracy` == metrics["accuracy"]
    - Use `@settings(max_examples=100)` and `@pytest.mark.pbt`
    - **Validates: Requirements 1.6, 1.7, 1.8**

  - [ ]* 1.3 Write property test for JSON round-trip (Property 2)
    - **Property 2: Metadata JSON round-trip**
    - In `ml/tests/test_metadata_properties.py`, add test that generates valid metadata dicts
    - Assert `json.loads(json.dumps(metadata)) == metadata`
    - Use `@settings(max_examples=100)` and `@pytest.mark.pbt`
    - **Validates: Requirements 5.1, 5.2**

- [x] 2. Implement metadata logging in scoring pipeline
  - [x] 2.1 Add `_load_metadata` function and integrate into `run_scoring` in `ml/predict.py`
    - Add `import json` at top
    - Define `_METADATA_PATH = _ML_DIR / "models" / "metadata.json"`
    - Implement `_load_metadata() -> dict | None` with graceful fallback (warning on missing file, try/except for invalid JSON)
    - After model load in `run_scoring`, call `_load_metadata()` and print `model_version` and `trained_at` to stdout
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 3. Checkpoint - Ensure training and scoring metadata work end-to-end
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Expose metadata in API responses
  - [x] 4.1 Add optional metadata fields to `AsteroidResponse` in `api/models.py`
    - Add `model_version: Optional[str] = None` field
    - Add `model_trained_at: Optional[str] = None` field
    - _Requirements: 3.1, 3.2_

  - [x] 4.2 Implement `_load_model_metadata` and inject into responses in `api/routers/asteroids.py`
    - Add `import json` and `from pathlib import Path`
    - Define `_METADATA_PATH = Path("/app/ml/models/metadata.json")`
    - Implement `_load_model_metadata() -> dict` with try/except for missing/invalid file returning `{}`
    - Call at module level: `_MODEL_METADATA = _load_model_metadata()`
    - Update `_row_to_asteroid` to inject `model_version=_MODEL_METADATA.get("model_version")` and `model_trained_at=_MODEL_METADATA.get("trained_at")`
    - _Requirements: 3.3, 3.4, 3.5, 3.6_

  - [ ]* 4.3 Write property test for metadata injection (Property 3)
    - **Property 3: Metadata injection into API responses**
    - Create `api/tests/test_metadata_properties.py`
    - Use hypothesis to generate metadata dicts with `model_version` and `trained_at` strings
    - Patch `_MODEL_METADATA` and assert `_row_to_asteroid(row).model_version == metadata["model_version"]` and `.model_trained_at == metadata["trained_at"]`
    - Use `@settings(max_examples=100)` and `@pytest.mark.pbt`
    - **Validates: Requirements 3.4, 3.5**

- [x] 5. Implement sklearn version compatibility test
  - [x] 5.1 Create `ml/tests/test_model_version.py`
    - Import `warnings`, `joblib`, `Path`, and `InconsistentVersionWarning` from `sklearn.exceptions`
    - Implement `test_model_version_compatibility` that loads the model with `warnings.catch_warnings(record=True)`
    - Filter for `InconsistentVersionWarning` and assert none are found
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 6. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The project uses pytest + hypothesis (already installed)
- All comments and docstrings should be in Portuguese to match existing codebase style
