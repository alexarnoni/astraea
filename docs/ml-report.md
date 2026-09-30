Astraea, relatorio do retarget do ML (fase 1)
==============================================
Gerado em 2026-09-30T02:55:20.825316+00:00. Alvo: is_potentially_hazardous. Features: relative_velocity_km_s, miss_distance_lunar, absolute_magnitude_h.
Nada aqui foi ajustado para melhorar metrica. Configuracao fixada antes da execucao.

1. Dados e prevalencia
- linhas brutas: 2083, asteroides (neo_id) distintos: 1822
- linhas usadas (sem nulos nas features): 2083, asteroides: 1822
- periodo: 2025-08-20 a 2026-09-30
- flag constante por neo_id: sim (0 neo_id com valores diferentes)
- prevalencia por linha: 0.0907 (189 linhas positivas)
- prevalencia por asteroide (ja positivo em alguma linha): 0.0988 (180 asteroides)
- nulos: {"relative_velocity_km_s": 0, "miss_distance_lunar": 0, "absolute_magnitude_h": 0, "diameter_avg_km": 0}; linhas descartadas por nulo: 0

2. Metricas por fold (classe positiva, threshold 0.5)
RandomForest:
  fold 1: P=0.7143 R=0.4878 F1=0.5797 PR-AUC=0.7477 n_teste=422 positivos=41 | tn=373 fp=8 fn=21 tp=20
  fold 2: P=0.5938 R=0.5135 F1=0.5507 PR-AUC=0.6480 n_teste=420 positivos=37 | tn=370 fp=13 fn=18 tp=19
  fold 3: P=0.5600 R=0.3590 F1=0.4375 PR-AUC=0.5767 n_teste=417 positivos=39 | tn=367 fp=11 fn=25 tp=14
  fold 4: P=0.6500 R=0.3939 F1=0.4906 PR-AUC=0.6552 n_teste=415 positivos=33 | tn=375 fp=7 fn=20 tp=13
  fold 5: P=0.6800 R=0.4359 F1=0.5312 PR-AUC=0.6131 n_teste=409 positivos=39 | tn=362 fp=8 fn=22 tp=17
  media (desvio): P=0.6396 (0.0561) R=0.4380 (0.0572) F1=0.5180 (0.0496) PR-AUC=0.6481 (0.0571)
  matriz agregada (soma dos folds): tn=1847 fp=47 fn=106 tp=83
Regressao logistica:
  fold 1: P=0.3529 R=0.1463 F1=0.2069 PR-AUC=0.3916 n_teste=422 positivos=41 | tn=370 fp=11 fn=35 tp=6
  fold 2: P=0.3636 R=0.1081 F1=0.1667 PR-AUC=0.4027 n_teste=420 positivos=37 | tn=376 fp=7 fn=33 tp=4
  fold 3: P=0.4000 R=0.2051 F1=0.2712 PR-AUC=0.4495 n_teste=417 positivos=39 | tn=366 fp=12 fn=31 tp=8
  fold 4: P=0.3889 R=0.2121 F1=0.2745 PR-AUC=0.4309 n_teste=415 positivos=33 | tn=371 fp=11 fn=26 tp=7
  fold 5: P=0.3889 R=0.1795 F1=0.2456 PR-AUC=0.4155 n_teste=409 positivos=39 | tn=359 fp=11 fn=32 tp=7
  media (desvio): P=0.3789 (0.0176) R=0.1702 (0.0387) F1=0.2330 (0.0410) PR-AUC=0.4180 (0.0205)
  matriz agregada (soma dos folds): tn=1842 fp=52 fn=157 tp=32
Classe majoritaria:
  fold 1: P=0.0000 R=0.0000 F1=0.0000 PR-AUC=0.0972 n_teste=422 positivos=41 | tn=381 fp=0 fn=41 tp=0
  fold 2: P=0.0000 R=0.0000 F1=0.0000 PR-AUC=0.0881 n_teste=420 positivos=37 | tn=383 fp=0 fn=37 tp=0
  fold 3: P=0.0000 R=0.0000 F1=0.0000 PR-AUC=0.0935 n_teste=417 positivos=39 | tn=378 fp=0 fn=39 tp=0
  fold 4: P=0.0000 R=0.0000 F1=0.0000 PR-AUC=0.0795 n_teste=415 positivos=33 | tn=382 fp=0 fn=33 tp=0
  fold 5: P=0.0000 R=0.0000 F1=0.0000 PR-AUC=0.0954 n_teste=409 positivos=39 | tn=370 fp=0 fn=39 tp=0
  media (desvio): P=0.0000 (0.0000) R=0.0000 (0.0000) F1=0.0000 (0.0000) PR-AUC=0.0907 (0.0064)
  matriz agregada (soma dos folds): tn=1894 fp=0 fn=189 tp=0
Nota: para o majoritario o score e constante, entao PR-AUC = prevalencia do fold (media 0.0907; PR-AUC medio medido 0.0907).

3. Avaliacao temporal
- corte por data: 2026-07-12 (treino 321 datas, teste 81 datas); linhas treino 1693, teste 390, positivos no teste 43
- neo_id do teste tambem presentes no treino: 95 de 390 (95 de 390 linhas)
- todas as linhas do teste:
  RandomForest: P=0.5417 R=0.3023 F1=0.3881 PR-AUC=0.5548 prevalencia=0.1103 | tn=336 fp=11 fn=30 tp=13
  Regressao logistica: P=0.4706 R=0.1860 F1=0.2667 PR-AUC=0.4180 prevalencia=0.1103 | tn=338 fp=9 fn=35 tp=8
  Classe majoritaria: P=0.0000 R=0.0000 F1=0.0000 PR-AUC=0.1103 prevalencia=0.1103 | tn=347 fp=0 fn=43 tp=0
- teste sem neo_id vistos no treino: 295 linhas, 38 positivos
  resultado:
  RandomForest: P=0.5455 R=0.3158 F1=0.4000 PR-AUC=0.5532 prevalencia=0.1288 | tn=247 fp=10 fn=26 tp=12
  Regressao logistica: P=0.4706 R=0.2105 F1=0.2909 PR-AUC=0.4145 prevalencia=0.1288 | tn=248 fp=9 fn=30 tp=8
  Classe majoritaria: P=0.0000 R=0.0000 F1=0.0000 PR-AUC=0.1288 prevalencia=0.1288 | tn=257 fp=0 fn=38 tp=0

4. diameter_avg_km versus absolute_magnitude_h
- Spearman: rho=-1.0000 (p=0, n=2083)
- RF sem diameter (3 features): precision=0.6396 recall=0.4380 f1=0.5180 pr_auc=0.6481
- RF com diameter (4 features): precision=0.6366 recall=0.4915 f1=0.5510 pr_auc=0.6531
- decisao registrada: conjunto final permanece sem diameter_avg_km.

5. Importancias (RF, media entre folds)
Impurity:
  relative_velocity_km_s: 0.1701
  miss_distance_lunar: 0.1613
  absolute_magnitude_h: 0.6685
Permutation (queda de PR-AUC no teste, media entre folds, desvio entre folds):
  relative_velocity_km_s: 0.0511 (0.0291)
  miss_distance_lunar: 0.2067 (0.0543)
  absolute_magnitude_h: 0.5097 (0.0494)

6. Referencia: regra H <= 22 (acrescentada depois da primeira execucao, sem ajuste)
Regra binaria: prediz positivo quando absolute_magnitude_h <= 22. PR-AUC nao se aplica.
  fold 1: P=0.4100 R=1.0000 F1=0.5816 | tn=322 fp=59 fn=0 tp=41
  fold 2: P=0.3627 R=1.0000 F1=0.5324 | tn=318 fp=65 fn=0 tp=37
  fold 3: P=0.4222 R=0.9744 F1=0.5891 | tn=326 fp=52 fn=1 tp=38
  fold 4: P=0.3837 R=1.0000 F1=0.5546 | tn=329 fp=53 fn=0 tp=33
  fold 5: P=0.3714 R=1.0000 F1=0.5417 | tn=304 fp=66 fn=0 tp=39
  media (desvio): P=0.3900 (0.0227) R=0.9949 (0.0103) F1=0.5599 (0.0221)
  matriz agregada (soma dos folds): tn=1599 fp=295 fn=1 tp=188
- temporal, todas as linhas do teste: P=0.3333 R=0.9767 F1=0.4970 | tn=263 fp=84 fn=1 tp=42
- temporal, sem neo_id vistos no treino: P=0.3162 R=0.9737 F1=0.4774 | tn=177 fp=80 fn=1 tp=37

7. Avisos
- desbalanceamento: prevalencia da classe positiva = 0.0907

8. Limitacoes
- A flag da NASA depende de H e da MOID (0,05 UA); a MOID nao e feature.
- miss_distance_lunar e a distancia de uma aproximacao especifica.
- Unidade de avaliacao e a linha; o mesmo asteroide tem varias linhas, por isso os folds agrupam por neo_id.

9. Analise exploratoria posterior (nao fez parte do plano original)
Acrescentada depois da primeira execucao. Nao altera nenhuma metrica das secoes 1 a 8.
Usa as probabilidades fora da amostra (out-of-fold) dos mesmos 5 folds (mesma seed), juntas em um conjunto.
Cada fold vem de um modelo diferente, entao o conjunto agrupado nao e o mesmo que a media dos folds.
Pontuacao -H: pontuacao = -absolute_magnitude_h, sem treinar nada.
9.1 e 9.2 Conjunto agrupado dos 5 folds:
  RandomForest: PR-AUC=0.6394
    recall >= 0.95: maior precisao=0.4045 (recall=0.9524, threshold=0.0700, 445 sinalizados para 189 positivos)
    recall >= 0.99: maior precisao=0.0907 (recall=1.0000, threshold=0.0000, 2083 sinalizados para 189 positivos)
  Regressao logistica: PR-AUC=0.4019
    recall >= 0.95: maior precisao=0.3327 (recall=0.9524, threshold=0.0862, 541 sinalizados para 189 positivos)
    recall >= 0.99: maior precisao=0.2961 (recall=0.9947, threshold=0.0655, 635 sinalizados para 189 positivos)
  -H (sem treino): PR-AUC=0.3592
    recall >= 0.95: maior precisao=0.3928 (recall=0.9788, threshold=-21.9200, 471 sinalizados para 189 positivos)
    recall >= 0.99: maior precisao=0.3892 (recall=0.9947, threshold=-22.0000, 483 sinalizados para 189 positivos)
  Regra H <= 22 no conjunto agrupado: precisao=0.3892 (a media entre folds publicada e 0.3900).
  Para comparar: PR-AUC do RF (media entre folds) = 0.6481, regressao logistica = 0.4180.
9.3 Split temporal (treino antigo, teste recente):
  RandomForest: PR-AUC=0.5548
    recall >= 0.95: maior precisao=0.3590 (recall=0.9767, threshold=0.0600, 117 sinalizados para 43 positivos)
    recall >= 0.99: maior precisao=0.1103 (recall=1.0000, threshold=0.0000, 390 sinalizados para 43 positivos)
  Regressao logistica: PR-AUC=0.4180
    recall >= 0.95: maior precisao=0.3178 (recall=0.9535, threshold=0.0803, 129 sinalizados para 43 positivos)
    recall >= 0.99: maior precisao=0.2945 (recall=1.0000, threshold=0.0669, 146 sinalizados para 43 positivos)
  -H (sem treino): PR-AUC=0.3564
    recall >= 0.95: maior precisao=0.3534 (recall=0.9535, threshold=-21.7900, 116 sinalizados para 43 positivos)
    recall >= 0.99: maior precisao=0.2966 (recall=1.0000, threshold=-22.4400, 145 sinalizados para 43 positivos)
  Regra H <= 22 no teste temporal: precisao=0.3333.
Nota sobre o RF com recall >= 0.99: no conjunto agrupado, 2 de 189 positivos recebem probabilidade exatamente 0 do RF. Alcancar esse recall exige incluir todo o conjunto (threshold 0), e a precisao cai para a prevalencia. Isso descreve a granularidade das probabilidades do RF, nao um ajuste.
Leitura: descricao apenas. Thresholds dos pontos de operacao sao lidos da curva e nao foram usados para escolher nem ajustar modelo. Com poucas centenas de positivos, as diferencas pequenas de precisao entre pontos vizinhos da curva sao instaveis.
