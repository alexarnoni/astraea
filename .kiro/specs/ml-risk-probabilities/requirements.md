# Documento de Requisitos — Probabilidades ML Completas

## Introdução

O sistema atual de análise de risco ML do Astraea descarta 2 das 3 probabilidades geradas pelo Random Forest (`predict_proba`), salvando apenas a probabilidade da classe predita em `risk_score_ml`. A UI exibe esse valor como "confiança" numa barra de gradiente que mistura eixo de nível de risco com probabilidade da classe — semanticamente incorreto. Este refactoring expõe as 3 probabilidades completas (baixo, médio, alto) em todas as camadas (ML → banco → API → frontend) e redesenha a UI para exibir a distribuição de probabilidade de forma cientificamente correta, seguindo padrões de scikit-learn e papers de classificação astronômica.

## Glossário

- **Scorer**: Módulo `ml/predict.py` que carrega o modelo treinado e executa predições batch na tabela `mart.mart_asteroids`
- **Modelo_RF**: Instância do `RandomForestClassifier` serializada em `ml/models/risk_classifier.joblib`
- **API_Asteroids**: Rotas FastAPI em `api/routers/asteroids.py` que servem dados de asteroides
- **AsteroidResponse**: Modelo Pydantic em `api/models.py` que define o schema de resposta da API
- **Detalhe_Page**: Página de detalhe do asteroide (`dashboard/js/detalhe.js` + `dashboard/detalhe.html`)
- **MetricCards**: Componente de cards de métricas renderizado por `renderMetricCards` em `detalhe.js`
- **MLPanel**: Componente de painel ML renderizado por `renderMLPanel` em `detalhe.js`
- **risk_proba_baixo**: Probabilidade atribuída pelo Modelo_RF à classe "baixo" (0.0 a 1.0)
- **risk_proba_medio**: Probabilidade atribuída pelo Modelo_RF à classe "médio" (0.0 a 1.0)
- **risk_proba_alto**: Probabilidade atribuída pelo Modelo_RF à classe "alto" (0.0 a 1.0)
- **risk_label_ml**: Classe predita pelo Modelo_RF (a de maior probabilidade)
- **mart_asteroids**: Tabela materializada pelo dbt em `mart.mart_asteroids`
- **Row_Mapper**: Função `_row_to_asteroid` em `api/routers/asteroids.py`

## Requisitos

### Requisito 1: Migração de schema — colunas de probabilidade

**User Story:** Como desenvolvedor, quero que as colunas de probabilidade sejam adicionadas via migração SQL manual, para que DDL não seja executado no caminho quente do Scorer.

#### Critérios de Aceitação

1. O desenvolvedor SHALL executar manualmente `ALTER TABLE mart.mart_asteroids ADD COLUMN IF NOT EXISTS risk_proba_baixo NUMERIC(6,4)` como migração SQL única antes do primeiro run do Scorer refatorado
2. O desenvolvedor SHALL executar manualmente `ALTER TABLE mart.mart_asteroids ADD COLUMN IF NOT EXISTS risk_proba_medio NUMERIC(6,4)` na mesma migração
3. O desenvolvedor SHALL executar manualmente `ALTER TABLE mart.mart_asteroids ADD COLUMN IF NOT EXISTS risk_proba_alto NUMERIC(6,4)` na mesma migração
4. THE Scorer SHALL NOT conter nenhum `ALTER TABLE` em momento algum — nem para adicionar nem para remover colunas

### Requisito 2: Validação de classes do modelo

**User Story:** Como desenvolvedor, quero que o Scorer valide as classes do Modelo_RF antes de extrair probabilidades, para que incompatibilidades entre classes treinadas e esperadas sejam detectadas imediatamente.

#### Critérios de Aceitação

1. WHEN o Scorer carrega o Modelo_RF, THE Scorer SHALL inspecionar `model.classes_` e identificar os rótulos exatos das três classes presentes
2. IF `model.classes_` não contiver exatamente três classes mapeáveis para baixo, médio e alto, THEN THE Scorer SHALL lançar um erro descritivo com as classes encontradas
3. THE Scorer SHALL mapear corretamente as classes independentemente de acentuação (aceitar tanto "medio" quanto "médio")
4. THE Scorer SHALL extrair os índices `idx_baixo`, `idx_medio` e `idx_alto` a partir de `model.classes_` usando o mapeamento validado

### Requisito 3: Extração e armazenamento das três probabilidades

**User Story:** Como desenvolvedor, quero que o Scorer extraia e armazene as três probabilidades completas do predict_proba, para que nenhuma informação do modelo seja descartada.

#### Critérios de Aceitação

1. WHEN o Scorer executa `model.predict_proba(X)`, THE Scorer SHALL extrair as três probabilidades (risk_proba_baixo, risk_proba_medio, risk_proba_alto) para cada registro usando os índices validados no Requisito 2
2. THE Scorer SHALL manter o campo `risk_label_ml` com a classe predita por `model.predict(X)`
3. THE Scorer SHALL remover toda referência ao campo `risk_score_ml` do código de geração de registros
4. THE Scorer SHALL construir cada registro do batch com os campos: neo_id, risk_proba_baixo, risk_proba_medio, risk_proba_alto, risk_label_ml
5. FOR ALL registros gerados pelo Scorer, a soma de risk_proba_baixo + risk_proba_medio + risk_proba_alto SHALL ser igual a 1.0 (com tolerância de ±0.0001 por arredondamento de ponto flutuante)

### Requisito 4: Granularidade do UPDATE

**User Story:** Como desenvolvedor, quero que o UPDATE do Scorer use a chave correta para evitar sobrescrever dados de aproximações distintas do mesmo asteroide.

#### Critérios de Aceitação

1. O desenvolvedor SHALL inspecionar a chave primária real de mart_asteroids antes da implementação, executando query de validação no banco
2. IF a tabela contiver múltiplas linhas por neo_id, THEN THE Scorer SHALL usar a chave composta (neo_id, feed_date) na cláusula WHERE do UPDATE
3. IF a tabela contiver apenas uma linha por neo_id, THEN THE Scorer SHALL manter a chave simples (neo_id) na cláusula WHERE do UPDATE

### Requisito 5: Modelo Pydantic — substituir risk_score_ml por probabilidades

**User Story:** Como desenvolvedor, quero que o AsteroidResponse exponha as três probabilidades em vez do score único, para que a API reflita a distribuição completa.

#### Critérios de Aceitação

1. THE AsteroidResponse SHALL conter o campo `risk_proba_baixo: Optional[float]` com valor padrão None
2. THE AsteroidResponse SHALL conter o campo `risk_proba_medio: Optional[float]` com valor padrão None
3. THE AsteroidResponse SHALL conter o campo `risk_proba_alto: Optional[float]` com valor padrão None
4. THE AsteroidResponse SHALL remover o campo `risk_score_ml`
5. THE AsteroidResponse SHALL manter o campo `risk_label_ml: Optional[str]` inalterado

### Requisito 6: Row Mapper — mapear novas colunas

**User Story:** Como desenvolvedor, quero que o Row_Mapper extraia as três probabilidades do resultado SQL, para que a API retorne os valores corretos.

#### Critérios de Aceitação

1. THE Row_Mapper SHALL extrair `risk_proba_baixo` da row usando `_safe_get` e converter para float quando não-nulo
2. THE Row_Mapper SHALL extrair `risk_proba_medio` da row usando `_safe_get` e converter para float quando não-nulo
3. THE Row_Mapper SHALL extrair `risk_proba_alto` da row usando `_safe_get` e converter para float quando não-nulo
4. THE Row_Mapper SHALL remover a extração do campo `risk_score_ml`
5. WHEN qualquer probabilidade for None no banco, THE Row_Mapper SHALL retornar None para esse campo no AsteroidResponse

### Requisito 7: Testes da API — atualizar fixtures

**User Story:** Como desenvolvedor, quero que os testes da API reflitam o novo schema de probabilidades, para que a suíte de testes valide o comportamento correto.

#### Critérios de Aceitação

1. THE test fixture `make_row` SHALL substituir `risk_score_ml=0.1` por `risk_proba_baixo=0.85, risk_proba_medio=0.10, risk_proba_alto=0.05`
2. THE test suite SHALL passar com sucesso após as alterações no modelo, router e fixtures
3. FOR ALL combinações de probabilidades geradas nos testes, THE Row_Mapper SHALL produzir um AsteroidResponse com os mesmos valores de probabilidade (round-trip)


### Requisito 8: MLPanel — redesenhar com distribuição de probabilidade

**User Story:** Como usuário, quero ver a distribuição completa de probabilidades do modelo ML em barras horizontais por classe, para que eu entenda a classificação de forma cientificamente correta.

#### Critérios de Aceitação

1. THE MLPanel SHALL remover completamente a UI antiga (número grande de porcentagem, texto "confiança", barra de gradiente com marcador, frase com "confiança")
2. THE MLPanel SHALL exibir um badge de risco (pill) com a classe predita baseada em `risk_label_ml`, usando as cores: baixo=#22c55e, médio=#f59e0b, alto=#ef4444
3. THE MLPanel SHALL exibir a frase "Classificado como [classe] risco com [X]% de probabilidade" onde X é `Math.round(proba_da_classe_predita * 100)` e a frase usa a fonte Inter 400, com a classe e porcentagem em Inter 500
4. THE MLPanel SHALL exibir três barras horizontais de probabilidade, uma para cada classe (baixo, médio, alto)
5. THE MLPanel SHALL colorir cada barra com a cor fixa da sua classe: baixo=#22c55e, médio=#f59e0b, alto=#ef4444, independentemente da classe predita
6. THE MLPanel SHALL exibir o valor de cada probabilidade como `Math.round(proba * 100)` seguido de "%"
7. THE MLPanel SHALL exibir o disclaimer "Este modelo não substitui avaliações oficiais da NASA" em itálico
8. IF qualquer uma das três probabilidades (risk_proba_baixo, risk_proba_medio, risk_proba_alto) for null, THEN THE MLPanel SHALL ocultar toda a seção de probabilidades e exibir "Análise de risco indisponível para este objeto"
9. THE MLPanel SHALL usar a palavra "probabilidade" em toda a interface, sem nenhuma menção a "confiança"

### Requisito 9: CSS das barras de probabilidade

**User Story:** Como desenvolvedor, quero que as barras de probabilidade sigam um layout consistente e animado, para que a UI seja visualmente clara e responsiva.

#### Critérios de Aceitação

1. THE Detalhe_Page SHALL estilizar `.proba-row` como grid de 3 colunas: label (60px) | barra (1fr) | valor (50px)
2. THE Detalhe_Page SHALL estilizar `.proba-bar-track` com height 8px, background rgba(255,255,255,0.05), border-radius 4px
3. THE Detalhe_Page SHALL estilizar `.proba-bar-fill` com height 8px, border-radius 4px, e transition de 0.4s ease na propriedade width
4. THE Detalhe_Page SHALL estilizar `.risk-badge` como pill com fonte Space Mono e texto uppercase
5. THE Detalhe_Page SHALL usar espaçamento de 12px entre cada `.proba-row`

### Requisito 10: MetricCards — atualizar card "Score ML"

**User Story:** Como usuário, quero que o card de métrica "Score ML" reflita a nova distribuição de probabilidade em vez do antigo score de confiança.

#### Critérios de Aceitação

1. THE MetricCards SHALL substituir o conteúdo do card "Score ML" para exibir a probabilidade da classe predita como `Math.round(proba * 100)` seguido de "% probabilidade"
2. THE MetricCards SHALL exibir o badge de risco ao lado do valor de probabilidade
3. THE MetricCards SHALL atualizar o tooltip do card para descrever que o valor representa a probabilidade atribuída pelo modelo à classe predita
4. THE MetricCards SHALL usar a palavra "probabilidade" no card, sem nenhuma menção a "confiança"

### Requisito 11: Restrições de escopo

**User Story:** Como desenvolvedor, quero que o refactoring respeite limites claros de escopo, para que mudanças não intencionais sejam evitadas.

#### Critérios de Aceitação

1. THE Scorer SHALL preservar a lógica de treinamento em `ml/train.py` sem modificações
2. THE API_Asteroids SHALL modificar apenas as rotas `/v1/asteroids/{neo_id}` e `/v1/asteroids` (incluindo `/v1/asteroids/upcoming`), sem alterar outras rotas
3. THE Detalhe_Page SHALL preservar o design system global (variáveis CSS em `:root`, fontes, cores base) sem modificações
4. THE refactoring SHALL preservar todas as dependências existentes sem adicionar novas bibliotecas ou pacotes

### Requisito 12: Eliminação do termo "confiança"

**User Story:** Como usuário, quero que toda a interface use "probabilidade" em vez de "confiança", para que a terminologia seja cientificamente precisa.

#### Critérios de Aceitação

1. THE Detalhe_Page SHALL substituir todas as ocorrências de "confiança" por "probabilidade" nos textos visíveis ao usuário
2. THE MetricCards SHALL substituir "confiança" por "probabilidade" no card e tooltip de Score ML
3. THE MLPanel SHALL usar exclusivamente "probabilidade" em labels, frases e tooltips

### Requisito 13: Remoção da coluna risk_score_ml (migração final separada)

**User Story:** Como desenvolvedor, quero remover a coluna obsoleta risk_score_ml somente após validar que as três probabilidades estão populadas, para que não haja perda de dados.

#### Critérios de Aceitação

1. O desenvolvedor SHALL executar a remoção de `risk_score_ml` apenas como última etapa do refactoring, após todas as outras camadas estarem funcionando e validadas
2. WHEN a remoção for executada, o desenvolvedor SHALL usar `ALTER TABLE mart.mart_asteroids DROP COLUMN IF EXISTS risk_score_ml` como migração SQL manual
