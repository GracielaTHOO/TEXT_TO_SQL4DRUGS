# Méthodologie d'évaluation

## Jeu de questions

`src/medsql/eval/questions.yaml` contient **90 questions** rédigées comme un utilisateur les
poserait : 60 questions originales (q001 à q060), chacune avec une requête SQL de référence, et
30 reformulations (q061 à q090). Une reformulation exprime la même intention avec d'autres mots
(synonymes, registre familier, ordre inversé, sigle) ; elle déclare sa source (`paraphrase_de`) et en
hérite la requête, la difficulté et la catégorie.

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

## Ablations (runs du 14 octobre 2026)

Quatre configurations pour Qwen2.5-Coder 1.5B et 7B, le même jour et sur la même BDPM.
Fichiers sources : `results/runs/20261014T*.json`. Écarts en points d'exactitude par rapport à la
configuration de base (few-shot, une auto-correction, sans libellés exacts).

| Variante | 1.5B | 7B |
|---|---:|---:|
| Base | 55,0 % | 63,3 % |
| Libellés exacts | **+3,3** | **+5,0** |
| Zero-shot (sans exemples) | −6,7 | 0,0 |
| Sans auto-correction | −3,3 | −1,7 |

- **Libellés exacts.** Sur le 7B, la variante gagne exactement les trois questions de disponibilité
  que le constat de S2 avait prédites (q017, q018, q041) et n'en perd aucune : la catégorie passe de
  0 % à 75 %. Sur le 1.5B, le bilan est de cinq questions gagnées et trois perdues, donc surtout du
  bruit. Le prompt grossit d'environ 500 tokens par question.
- **Exemples few-shot.** Ils comptent pour le petit modèle (−6,7 points sans eux, dont −16 points
  sur les questions faciles) et pas pour le 7B.
- **Auto-correction.** Elle rattrape surtout des requêtes non exécutables : sans elle, le SQL
  exécutable baisse de 95 % à 88 % (1.5B) et de 100 % à 95 % (7B).
- **Variabilité entre deux jours.** La configuration de base du 1.5B obtient 55,0 % ce jour contre
  56,7 % le 12 octobre, sur une BDPM mise à jour entre-temps. Les écarts de un à deux points ne sont
  pas interprétables seuls ; les tests appariés arrivent en S6.

## Analyse des erreurs (configuration par défaut, v0.2.0)

`medsql.eval.errors` attribue à chaque réponse fausse **une** cause, la première qui s'applique
dans cet ordre : pas de réponse du modèle, SQL non exécutable, table nécessaire absente, table en
trop ou jointure sur d'autres colonnes, agrégat différent, valeur de filtre texte différente, puis,
à structure identique, lignes en trop, lignes manquantes ou valeurs différentes. La comparaison
porte sur les requêtes analysées par sqlglot (tables hors CTE, clés de jointure, agrégats, littéraux
texte sans accents ni jokers) et sur les nombres de lignes enregistrés : rien n'est réexécuté.

| Cause | 1.5B | 3B | 7B |
|---|---:|---:|---:|
| SQL non exécutable | 5 | 4 | 0 |
| Table absente | 4 | 5 | 2 |
| Jointure | 5 | 4 | 6 |
| Agrégat | 4 | 6 | 5 |
| Filtre texte | 1 | 2 | 4 |
| Nombre de lignes | 1 | 1 | 1 |
| Valeurs | 5 | 2 | 1 |
| **Réponses fausses** | **25** | **24** | **19** |
| Exactitude | 58,3 % | 60,0 % | 68,3 % |

Runs : 1.5B et 7B du 14 octobre, 3B du 16 octobre (libellés exacts, few-shot, une auto-correction).

- Les jointures et les agrégats concentrent 30 des 68 erreurs. Les agrégats sont surtout
  `COUNT(*)` contre `COUNT(DISTINCT …)` : le modèle compte des spécialités là où la référence compte
  des lignes, ou l'inverse (q056, q057). Une partie de ces cas relève d'une question ambiguë plus que
  d'une erreur ; ils seront relus en S7, avec les paraphrases.
- Le SQL non exécutable disparaît avec la taille : 5 requêtes pour le 1.5B, aucune pour le 7B.
- La catégorie « jointure » inclut des jointures inutiles mais inoffensives (par exemple vers
  `medicaments` alors que `avis_smr` suffit) quand la réponse est fausse pour une autre raison :
  la cause retenue est la première dans l'ordre, pas forcément la seule.

## Incertitude et significativité (S6)

`medsql.eval.significance` ajoute deux mesures, calculées à partir des runs enregistrés :

- **Intervalle de confiance à 95 %** de l'exactitude, par bootstrap percentile sur les questions
  (10 000 rééchantillonnages, graine fixe : le résultat est reproductible). Il figure dans le README,
  le classement et, sous forme de moustaches, dans le graphique du tableau de bord.
- **Test exact de McNemar** entre deux runs, sur leurs questions communes appariées par identifiant.
  Seules comptent les questions discordantes (juste pour l'un, faux pour l'autre) ; la p-valeur est
  binomiale bilatérale. Il compare les modèles deux à deux (section *Les écarts sont-ils réels ?*) et
  chaque ablation à son run de référence.

Résultats sur la configuration par défaut :

| Comparaison | Justes pour A seul | Justes pour B seul | p |
|---|---:|---:|---:|
| 7B contre 3B | 10 | 5 | 0,30 |
| 7B contre 1.5B | 13 | 7 | 0,26 |
| 3B contre 1.5B | 8 | 7 | 1,00 |
| 7B avec contre sans libellés exacts | 3 | 0 | 0,25 |

- Aucun écart n'est significatif au seuil de 5 %, pas même 7B contre 1.5B (10 points d'écart).
  Les intervalles se recouvrent largement : 7B 56,7 – 80,0 %, 1.5B 46,7 – 70,0 %.
- Le gain des libellés exacts sur le 7B est en revanche **expliqué** : les trois questions gagnées
  sont celles que le constat de S2 avait prédites. Une cause identifiée vaut ici plus qu'une p-valeur
  calculée sur trois questions.
- **Puissance.** Avec le profil observé entre 7B et 1.5B (un tiers de questions discordantes,
  partagées 65/35), la probabilité de détecter l'écart au seuil de 5 % est d'environ 20 % avec 60
  questions, 42 % avec 120, 66 % avec 200 et 84 % avec 300. Le passage à 120 questions (S7, S8) ne
  suffira donc pas à départager deux modèles proches.
- Les runs comparés datent de jours différents (14 et 16 octobre) : la BDPM a pu changer entre-temps,
  ce qui ajoute une source de variation que le test ne voit pas.

## Limites connues

- 60 questions donnent un intervalle de confiance à 95 % d'environ ±12 points : aucun des écarts
  mesurés jusqu'ici n'est significatif (voir *Incertitude et significativité*).
- Les questions ont été rédigées par l'auteur du projet, avec un biais possible vers des
  formulations proches du schéma.
- Une question ambiguë peut admettre plusieurs requêtes correctes ; la référence en retient une.
