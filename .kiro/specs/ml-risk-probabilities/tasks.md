# Plano de Implementação: Probabilidades ML Completas

## Visão Geral

Refatoração do pipeline de scoring ML para expor as três probabilidades completas (`risk_proba_baixo`, `risk_proba_medio`, `risk_proba_alto`) em todas as camadas do sistema, substituindo o campo único `risk_score_ml`. A implementação segue a ordem: migração SQL → Scorer → API → frontend → migração final.

## Tarefas

- [x] 1. Criar script de migração SQL para adicionar colunas de probabilidade
  - Criar arquivo `scripts/add_risk_proba_columns.sql` com os três `ALTER TABLE mart.mart_asteroids ADD COLUMN IF NOT EXISTS` para `risk_proba_baixo NUMERIC(6,4)`, `risk_proba_medio NUMERIC(6,4)` e `risk_proba_alto NUMERIC(6,4)`
  - O script NÃO deve ser executado automaticamente — o desenvolvedor executa manualmente
  - _Requisitos: 1.1, 1.2, 1.3_

- [x] 2. Refatorar o Scorer (`ml/predict.py`)
  - [x] 2.1 Implementar função `_validate_and_map_classes(model)` com tolerância de acentuação
    - Usar `unicodedata.normalize('NFD')` para normalizar acentos
    - Mapear cada classe de `model.classes_` para forma canônica sem acento (`baixo`, `medio`, `alto`)
    - Lançar `ValueError` descritivo se não houver exatamente 3 classes mapeáveis
    - Retornar `dict[str, int]` com `{'baixo': idx, 'medio': idx, 'alto': idx}`
    - _Requisitos: 2.1, 2.2, 2.3, 2.4_

  - [x]* 2.2 Escrever teste de propriedade P1: Validação de classes com tolerância de acentuação
    - **Propriedade 1: Validação de classes com tolerância de acentuação**
    - Para qualquer permutação de `['baixo', 'medio'/'médio', 'alto']`, a função retorna mapeamento correto
    - Usar `hypothesis` com mínimo 100 exemplos
    - Criar arquivo `ml/tests/test_predict_probabilities.py`
    - **Valida: Requisitos 2.1, 2.3, 2.4**

  - [x]* 2.3 Escrever teste de propriedade P2: Rejeição de classes inválidas
    - **Propriedade 2: Rejeição de classes inválidas**
    - Para qualquer array que não contenha exatamente 3 classes mapeáveis, a função lança `ValueError`
    - Usar `hypothesis` com mínimo 100 exemplos
    - **Valida: Requisito 2.2**

  - [x] 2.4 Refatorar `run_scoring()` para extrair as três probabilidades e usar chave composta
    - Adicionar `feed_date` ao SELECT de dados (`SELECT neo_id, feed_date, ...`)
    - Chamar `_validate_and_map_classes(model)` para obter índices
    - Extrair `risk_proba_baixo`, `risk_proba_medio`, `risk_proba_alto` de `model.predict_proba(X)` usando os índices validados
    - Construir records com `neo_id`, `feed_date`, `risk_proba_baixo`, `risk_proba_medio`, `risk_proba_alto`, `risk_label_ml`
    - UPDATE com `WHERE neo_id = :neo_id AND feed_date = :feed_date`
    - Remover os dois `ALTER TABLE ... ADD COLUMN` existentes (risk_score_ml e risk_label_ml)
    - Remover toda referência a `risk_score_ml` na construção de records
    - O Scorer NÃO deve conter nenhum `ALTER TABLE`
    - _Requisitos: 1.4, 3.1, 3.2, 3.3, 3.4, 4.2_

  - [x]* 2.5 Escrever teste de propriedade P3: Extração de probabilidades preserva ordem e valores
    - **Propriedade 3: Extração de probabilidades preserva ordem e valores**
    - Para qualquer array numpy (n, 3) com linhas somando 1.0 e qualquer mapeamento de índices válido, a extração retorna valores corretos
    - Usar `hypothesis` com `hypothesis.extra.numpy` e mínimo 100 exemplos
    - **Valida: Requisitos 3.1, 3.4**

- [x] 3. Checkpoint — Validar camada ML
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Atualizar camada API
  - [x] 4.1 Atualizar modelo Pydantic `AsteroidResponse` em `api/models.py`
    - Remover campo `risk_score_ml: Optional[float]`
    - Adicionar `risk_proba_baixo: Optional[float] = None`
    - Adicionar `risk_proba_medio: Optional[float] = None`
    - Adicionar `risk_proba_alto: Optional[float] = None`
    - Manter `risk_label_ml: Optional[str] = None` inalterado
    - _Requisitos: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 4.2 Atualizar Row Mapper `_row_to_asteroid` em `api/routers/asteroids.py`
    - Substituir extração de `risk_score_ml` por extração de `risk_proba_baixo`, `risk_proba_medio`, `risk_proba_alto` usando `_safe_get` com conversão para float
    - _Requisitos: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 4.3 Atualizar fixtures e testes da API em `api/tests/test_asteroids_router.py`
    - Substituir `risk_score_ml=0.1` na fixture `make_row` por `risk_proba_baixo=0.85, risk_proba_medio=0.10, risk_proba_alto=0.05`
    - Atualizar o teste de propriedade existente (round-trip) para validar os novos campos de probabilidade
    - _Requisitos: 7.1, 7.2_

  - [x]* 4.4 Escrever teste de propriedade P4: Round-trip do Row Mapper com probabilidades
    - **Propriedade 4: Round-trip do Row Mapper com probabilidades**
    - Para qualquer combinação de `(float | None)` nos campos `risk_proba_baixo`, `risk_proba_medio`, `risk_proba_alto`, `_row_to_asteroid` produz `AsteroidResponse` com os mesmos valores
    - Usar `hypothesis` com mínimo 100 exemplos
    - **Valida: Requisitos 6.1, 6.2, 6.3, 6.5, 7.3**

- [x] 5. Checkpoint — Validar camada API
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Atualizar frontend — CSS e JavaScript
  - [x] 6.1 Adicionar classes CSS de probabilidade em `dashboard/css/style.css`
    - Adicionar `.proba-row` (grid 3 colunas: 60px | 1fr | 50px), `.proba-row + .proba-row` (margin-top 12px)
    - Adicionar `.proba-row__label` (Space Mono, 0.7rem, uppercase, muted)
    - Adicionar `.proba-row__value` (Space Mono, 0.8rem, text-align right)
    - Adicionar `.proba-bar-track` (height 8px, background rgba(255,255,255,0.05), border-radius 4px)
    - Adicionar `.proba-bar-fill` (height 8px, border-radius 4px, transition width 0.4s ease)
    - Adicionar `.risk-badge`, `.risk-badge--baixo`, `.risk-badge--medio` (sem acento), `.risk-badge--alto`
    - _Requisitos: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [x] 6.2a Implementar função utilitária `normalizeRiskClass(label)` em `dashboard/js/detalhe.js`
    - Criar função que normaliza acentos via `String.normalize('NFD')` + regex, retornando sempre `'baixo'`, `'medio'` ou `'alto'` (sem acento)
    - Incluir teste unitário inline ou em `dashboard/tests/detalhe.test.js` verificando que `'médio'` → `'medio'`, `'medio'` → `'medio'`, `'MÉDIO'` → `'medio'`, etc.

  - [x] 6.2b Reescrever `renderMLPanel` em `dashboard/js/detalhe.js` usando `normalizeRiskClass`
    - Toda construção de className (`.risk-badge--{classe}`, `.proba-bar-fill`) deve usar `normalizeRiskClass`
    - Se qualquer probabilidade for `null` → exibir "Análise de risco indisponível para este objeto"
    - Caso contrário: badge de risco, frase "Classificado como {classe} risco com {X}% de probabilidade", 3 barras `.proba-row`, disclaimer
    - Cores fixas: baixo=#22c55e, médio=#f59e0b, alto=#ef4444
    - Usar "probabilidade" em toda a interface, sem nenhuma menção a "confiança"
    - _Requisitos: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9, 12.1, 12.3_

  - [x] 6.3 Atualizar `renderMetricCards` em `dashboard/js/detalhe.js`
    - Substituir conteúdo do card "Score ML": exibir `Math.round(proba_da_classe_predita * 100)` + "% probabilidade" + badge
    - Atualizar tooltip para descrever probabilidade da classe predita
    - Remover toda menção a "confiança"
    - _Requisitos: 10.1, 10.2, 10.3, 10.4, 12.2_

  - [x] 6.4 Remover CSS inline obsoleto de `dashboard/detalhe.html`
    - Remover regras `.risk-scale`, `.risk-scale__low`, `.risk-scale__mid`, `.risk-scale__high`, `.risk-scale__marker`, `.risk-scale-wrap`, `.risk-scale-labels` do bloco `<style>` inline
    - _Requisitos: 8.1_

  - [x]* 6.5 Escrever teste de propriedade P5: MLPanel renderiza distribuição completa
    - **Propriedade 5: MLPanel renderiza distribuição completa**
    - Para qualquer asteroide com 3 probabilidades não-nulas (somando ≈1.0) e `risk_label_ml` válido, o HTML contém badge, frase com porcentagem e 3 barras `.proba-row`
    - Usar `fast-check` com mínimo 100 exemplos em `dashboard/tests/detalhe.test.js`
    - **Valida: Requisitos 8.2, 8.3, 8.4, 8.6**

  - [x]* 6.6 Escrever teste de propriedade P6: MLPanel oculta seção quando probabilidade é null
    - **Propriedade 6: MLPanel oculta seção quando probabilidade é null**
    - Para qualquer asteroide com pelo menos uma probabilidade `null`, o HTML exibe "Análise de risco indisponível" e não contém barras
    - Usar `fast-check` com mínimo 100 exemplos
    - **Valida: Requisito 8.8**

  - [x]* 6.7 Escrever teste de propriedade P7: Eliminação do termo "confiança"
    - **Propriedade 7: Eliminação do termo confiança**
    - Para qualquer asteroide com dados válidos, a saída HTML de `renderMLPanel` e `renderMetricCards` não contém "confiança"
    - Usar `fast-check` com mínimo 100 exemplos
    - **Valida: Requisitos 8.9, 10.4, 12.1, 12.2, 12.3**

- [ ] 7. Checkpoint — Validar frontend
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Criar script de migração final para remover `risk_score_ml`
  - Criar arquivo `scripts/drop_risk_score_ml.sql` com `ALTER TABLE mart.mart_asteroids DROP COLUMN IF EXISTS risk_score_ml`
  - O script NÃO deve ser executado automaticamente — o desenvolvedor executa manualmente como última etapa, após todas as camadas estarem validadas
  - _Requisitos: 13.1, 13.2_

## Notas

- Tarefas marcadas com `*` são opcionais e podem ser puladas para um MVP mais rápido
- Cada tarefa referencia requisitos específicos para rastreabilidade
- Checkpoints garantem validação incremental entre camadas
- Testes de propriedade validam propriedades universais de corretude
- Restrições de escopo: NÃO modificar `train.py`, NÃO alterar outras rotas, NÃO mudar design system global, NÃO adicionar dependências (Requisito 11)
