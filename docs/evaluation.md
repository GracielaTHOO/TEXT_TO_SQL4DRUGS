# Méthodologie d'évaluation

## Jeu de questions

`src/medsql/eval/questions.yaml` contient **60 questions** rédigées comme un utilisateur les
poserait, chacune avec une requête SQL de référence.

| Difficulté | Définition |
|---|---|
| facile | une table, un filtre ou un agrégat simple |
| moyen | une jointure, un `GROUP BY`, un classement ou une date |
| difficile | plusieurs jointures, sous-requêtes, auto-jointure, pourcentages |

Les dix catégories (comptage, filtrage, jointures, agrégations, classements, dates, prix,
génériques, avis HAS, ruptures) couvrent toutes les tables de la base.

**Réponses recalculées.** On ne stocke pas les réponses attendues : elles sont obtenues en exécutant
la requête de référence sur la base du jour. Le jeu reste valide à chaque mise à jour mensuelle de la BDPM.

**Pas de fuite.** Les exemples few-shot du prompt sont distincts des questions évaluées
(test `test_no_leakage_between_few_shots_and_eval`).

## Métriques

| Métrique | Définition |
|---|---|
| **Exactitude** (référence) | Le résultat d'exécution de la requête générée contient exactement les lignes de la référence. Des colonnes supplémentaires ou réordonnées sont acceptées (« les médicaments X » avec leur code CIS en plus reste juste). |
| Exactitude stricte | Mêmes lignes et mêmes colonnes, dans le même ordre de colonnes. |
| SQL exécutable | Part des questions pour lesquelles une requête valide a été exécutée sans erreur. |
| Réparées | Questions rattrapées par l'auto-correction après une première erreur SQL. |
| Latence p50 / p95 | Temps total par question (génération, réparation éventuelle, exécution). |
| Tokens / question | Tokens de prompt et de complétion, tels que rapportés par le serveur. |

Règles de comparaison :
- l'ordre des lignes est ignoré, sauf pour les questions marquées `ordonne: true` (classements) ;
- les nombres sont arrondis à une décimale (un modèle qui arrondit 37,12 % en 37,1 % n'est pas pénalisé) ;
- `3` et `3.0` sont égaux ; les chaînes sont comparées après suppression des espaces aux extrémités.

Cette métrique suit l'*execution accuracy* de [Spider](https://yale-lily.github.io/spider) et
[BIRD](https://bird-bench.github.io/), avec la tolérance sur les colonnes en plus de BIRD.

## Protocole

- température 0 et graine fixe : les runs sont reproductibles à matériel identique ;
- chaque run enregistre le modèle, la configuration, la version du code (commit), l'empreinte
  du jeu de questions et la date de téléchargement de la BDPM ;
- seuls les runs complets (sans `--limit`) entrent au classement ;
- une requête de référence qui renvoie zéro ligne lève un avertissement dans le run :
  la question doit être revue, car un modèle qui renvoie aussi zéro ligne serait compté juste.
  `medsql check-questions` fait ce contrôle sur la base réelle avant chaque évaluation ;
- la génération est plafonnée à 512 tokens et chaque appel au modèle à 180 s : au-delà,
  la question est comptée fausse (`LLMError`) et l'évaluation continue.

## Lancer une évaluation

```bash
ollama pull qwen2.5-coder:7b
medsql eval --model qwen2.5-coder:7b             # few-shot + 1 tour d'auto-correction
medsql eval --model qwen2.5-coder:7b --zero-shot # ablation : sans exemples
medsql eval --model qwen2.5-coder:7b --repairs 0 # ablation : sans auto-correction
medsql eval --model qwen2.5-coder:7b --value-hints # ablation : libellés exacts dans le prompt
medsql report                                    # tableau de bord + README
```

Sur GitHub, le workflow *Évaluation des modèles* prend une entrée `configs` (par défaut `base`) :
`base`, `zero-shot`, `sans-correction` et `libelles`, séparées par des virgules. Chaque configuration
est évaluée pour chaque modèle. Le tableau de bord compare alors chaque variante à la configuration de
base du même modèle (section *Ablations*).

L'option `--value-hints` lit dans la base les valeurs des colonnes catégorielles qui en ont au plus 12
(statut de disponibilité, SMR, ASMR, type de générique…) et les ajoute au schéma du prompt, écrites
comme des littéraux SQL.

## Premiers constats (runs du 12 octobre 2026)

Trois tailles de Qwen2.5-Coder, mêmes 60 questions, même prompt (few-shot et une auto-correction),
CPU du runner GitHub. Fichiers sources : `results/runs/20261012T*.json`.

| Modèle | Exactitude | Stricte | SQL exécutable | Facile | Moyen | Difficile | Latence p50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1.5B | 56,7 % | 38,3 % | 91,7 % | 80 % | 54 % | 0 % | 4,2 s |
| 3B | 56,7 % | 41,7 % | 91,7 % | 80 % | 46 % | 22 % | 7,4 s |
| 7B | 60,0 % | 48,3 % | 96,7 % | 80 % | 58 % | 11 % | 17,0 s |

- Les trois modèles sont à égalité sur les questions faciles. Le 7B gagne surtout en SQL exécutable
  et en exactitude stricte, pour une latence quatre fois plus élevée que le 1.5B.
- Les écarts d'exactitude (3,3 points) restent dans la marge d'incertitude de 60 questions
  (voir plus bas) : les intervalles de confiance arrivent en S6.
- Les jointures sont le point faible commun (29 %, 0 % et 14 %).
- **Libellés devinés.** Sur les ruptures et tensions, le 7B obtient 0 sur 4 : il filtre
  `statut = 'Rupture'` ou `'Tension'` alors que les libellés réels sont « Rupture de stock » et
  « Tension d'approvisionnement ». Le schéma du prompt ne donne pas ces libellés exacts. Leur ajout
  est mesuré en S3 comme une ablation, pour que les chiffres ci-dessus restent comparables.

## Limites connues

- 60 questions donnent un intervalle de confiance à 95 % d'environ ±12 points autour de 50 % :
  un écart de quelques points entre deux modèles n'est pas significatif.
- Les questions ont été rédigées par l'auteur du projet, avec un biais possible vers des
  formulations proches du schéma.
- Une question ambiguë peut admettre plusieurs requêtes correctes ; la référence en retient une.
