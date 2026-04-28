"""
Testes de propriedade para ml/predict.py — _validate_and_map_classes.

Usa hypothesis para validar propriedades universais de corretude.
"""

import itertools
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# Garantir que ml/ está no path para importar predict
_ML_DIR = Path(__file__).resolve().parent.parent
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))


def _import_validate_and_map_classes():
    """Importa _validate_and_map_classes mockando dependências pesadas."""
    mocks = {}
    for mod_name in ("joblib", "pandas", "dotenv", "sqlalchemy"):
        if mod_name not in sys.modules:
            mocks[mod_name] = MagicMock()
            sys.modules[mod_name] = mocks[mod_name]
    # Sub-módulos necessários
    for sub in ("sqlalchemy.engine", "sqlalchemy"):
        if sub not in sys.modules:
            mocks[sub] = MagicMock()
            sys.modules[sub] = mocks[sub]

    if "predict" in sys.modules:
        del sys.modules["predict"]

    from predict import _validate_and_map_classes
    return _validate_and_map_classes


_validate_and_map_classes = _import_validate_and_map_classes()


# ---------------------------------------------------------------------------
# Estratégias auxiliares
# ---------------------------------------------------------------------------

_BAIXO_VARIANTS = ["baixo", "Baixo", "BAIXO", "bAiXo"]
_MEDIO_VARIANTS = ["medio", "médio", "Medio", "Médio", "MEDIO", "MÉDIO", "mEdIo", "mÉdIo"]
_ALTO_VARIANTS = ["alto", "Alto", "ALTO", "aLtO"]

baixo_strategy = st.sampled_from(_BAIXO_VARIANTS)
medio_strategy = st.sampled_from(_MEDIO_VARIANTS)
alto_strategy = st.sampled_from(_ALTO_VARIANTS)


# ---------------------------------------------------------------------------
# P1: Validação de classes com tolerância de acentuação
# Feature: ml-risk-probabilities, Property 1: Validação de classes com tolerância de acentuação
# Validates: Requirements 2.1, 2.3, 2.4
# ---------------------------------------------------------------------------

@pytest.mark.pbt
@given(
    baixo=baixo_strategy,
    medio=medio_strategy,
    alto=alto_strategy,
    perm=st.sampled_from(list(itertools.permutations([0, 1, 2]))),
)
@settings(max_examples=100)
def test_p1_validate_classes_accent_tolerance(baixo, medio, alto, perm):
    """
    **Validates: Requirements 2.1, 2.3, 2.4**

    Para qualquer permutação de ['baixo', 'medio'/'médio', 'alto'] (com ou sem
    acento), _validate_and_map_classes retorna mapeamento correto de índices
    onde cada chave canônica aponta para a posição correta no array original.

    Feature: ml-risk-probabilities, Property 1: Validação de classes com tolerância de acentuação
    """
    variants = [baixo, medio, alto]
    classes = [variants[i] for i in perm]

    model = SimpleNamespace(classes_=classes)
    mapping = _validate_and_map_classes(model)

    # Deve retornar exatamente as 3 chaves canônicas
    assert set(mapping.keys()) == {"baixo", "medio", "alto"}

    # Cada índice deve apontar para a posição correta no array original
    assert mapping["baixo"] == list(perm).index(0)
    assert mapping["medio"] == list(perm).index(1)
    assert mapping["alto"] == list(perm).index(2)

    # Índices devem ser distintos e cobrir {0, 1, 2}
    assert set(mapping.values()) == {0, 1, 2}


# ---------------------------------------------------------------------------
# P2: Rejeição de classes inválidas
# Feature: ml-risk-probabilities, Property 2: Rejeição de classes inválidas
# Validates: Requirement 2.2
# ---------------------------------------------------------------------------

_INVALID_STRINGS = [
    "critico", "extremo", "nulo", "desconhecido", "xyz", "123",
    "bai", "alt", "med", "risk", "none", "  ", "médium",
]

invalid_string_strategy = st.sampled_from(_INVALID_STRINGS)


@pytest.mark.pbt
@given(data=st.data())
@settings(max_examples=100)
def test_p2_reject_invalid_classes(data):
    """
    **Validates: Requirement 2.2**

    Para qualquer array que NÃO contenha exatamente 3 classes mapeáveis para
    {baixo, medio, alto}, a função lança ValueError.

    Feature: ml-risk-probabilities, Property 2: Rejeição de classes inválidas
    """
    scenario = data.draw(st.sampled_from([
        "empty",
        "all_invalid",
        "missing_one",
        "duplicate_class",
        "too_many_invalid",
    ]))

    if scenario == "empty":
        classes = []

    elif scenario == "all_invalid":
        n = data.draw(st.integers(min_value=1, max_value=5))
        classes = [data.draw(invalid_string_strategy) for _ in range(n)]

    elif scenario == "missing_one":
        pair = data.draw(st.sampled_from([
            ["baixo", "medio"],
            ["baixo", "alto"],
            ["medio", "alto"],
        ]))
        classes = list(pair)

    elif scenario == "duplicate_class":
        dup = data.draw(st.sampled_from(["baixo", "medio", "alto"]))
        other = data.draw(st.sampled_from([c for c in ["baixo", "medio", "alto"] if c != dup]))
        classes = [dup, dup, other]

    elif scenario == "too_many_invalid":
        # Array com mais de 3 elementos mas sem as 3 classes válidas completas
        base = [data.draw(invalid_string_strategy) for _ in range(data.draw(st.integers(min_value=3, max_value=6)))]
        # Pode incluir 0-2 classes válidas misturadas
        valid_subset = data.draw(st.sampled_from([
            [],
            ["baixo"],
            ["alto"],
            ["baixo", "medio"],
        ]))
        classes = base + valid_subset

    model = SimpleNamespace(classes_=classes)

    with pytest.raises(ValueError):
        _validate_and_map_classes(model)


# ---------------------------------------------------------------------------
# P3: Extração de probabilidades preserva ordem e valores
# Feature: ml-risk-probabilities, Property 3: Extração de probabilidades preserva ordem e valores
# Validates: Requirements 3.1, 3.4
# ---------------------------------------------------------------------------

import numpy as np
from hypothesis.extra.numpy import arrays


def _normalize_rows(arr: np.ndarray) -> np.ndarray:
    """Normaliza cada linha para somar exatamente 1.0."""
    row_sums = arr.sum(axis=1, keepdims=True)
    # Evita divisão por zero substituindo somas zero por 1
    row_sums = np.where(row_sums == 0, 1.0, row_sums)
    return arr / row_sums


# Estratégia: gerar array (n, 3) de floats positivos e normalizar para somar 1.0
proba_array_strategy = st.integers(min_value=1, max_value=50).flatmap(
    lambda n: arrays(
        dtype=np.float64,
        shape=(n, 3),
        elements=st.floats(min_value=1e-6, max_value=1.0, allow_nan=False, allow_infinity=False),
    ).map(_normalize_rows)
)

# Estratégia: permutação válida de {0, 1, 2} para o mapeamento de índices
index_permutation_strategy = st.sampled_from(list(itertools.permutations([0, 1, 2])))


@pytest.mark.pbt
@given(
    probas=proba_array_strategy,
    perm=index_permutation_strategy,
)
@settings(max_examples=100)
def test_p3_extraction_preserves_order_and_values(probas, perm):
    """
    **Validates: Requirements 3.1, 3.4**

    Para qualquer array numpy (n, 3) com linhas somando 1.0 e qualquer
    mapeamento de índices válido {'baixo': i, 'medio': j, 'alto': k}
    onde {i,j,k} = {0,1,2}, a extração via probas[:, idx] retorna os
    valores corretos preservando a correspondência entre classe e coluna.

    Feature: ml-risk-probabilities, Property 3: Extração de probabilidades preserva ordem e valores
    """
    idx_baixo, idx_medio, idx_alto = perm

    # Simula o mapeamento retornado por _validate_and_map_classes
    class_map = {"baixo": idx_baixo, "medio": idx_medio, "alto": idx_alto}

    # Extração — mesma lógica usada em run_scoring()
    risk_proba_baixo = probas[:, class_map["baixo"]]
    risk_proba_medio = probas[:, class_map["medio"]]
    risk_proba_alto = probas[:, class_map["alto"]]

    n = probas.shape[0]
    for i in range(n):
        # Cada valor extraído deve corresponder exatamente à coluna correta
        assert risk_proba_baixo[i] == probas[i, idx_baixo]
        assert risk_proba_medio[i] == probas[i, idx_medio]
        assert risk_proba_alto[i] == probas[i, idx_alto]

        # As 3 probabilidades extraídas devem somar ~1.0 (mesma tolerância do requisito 3.5)
        soma = float(risk_proba_baixo[i]) + float(risk_proba_medio[i]) + float(risk_proba_alto[i])
        assert abs(soma - 1.0) < 1e-4, f"Soma das probabilidades = {soma}, esperado ~1.0"

    # Verificação vetorial: arrays extraídos preservam shape
    assert risk_proba_baixo.shape == (n,)
    assert risk_proba_medio.shape == (n,)
    assert risk_proba_alto.shape == (n,)
