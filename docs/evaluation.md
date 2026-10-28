# Méthodologie d'évaluation

## Jeu de questions

`src/medsql/eval/questions.yaml` contient **120 questions** rédigées comme un utilisateur les
poserait :

- 80 questions originales (q001 à q060, puis q091 à q110 depuis S8), chacune avec une requête SQL
  de référence ;
- 30 reformulations (q061 à q090). Une reformulation exprime la même intention avec d'autres mots
  (synonymes, registre familier, ordre inversé, sigle) ; elle déclare sa source (`paraphrase_de`) et
  en hérite la requête, la difficulté et la catégorie ;
- 10 questions **hors périmètre** (q111 à q120, `hors_perimetre: true`), sans requête : la base ne
  permet pas d'y répondre et la seule bonne réponse est de s'abstenir (voir *Abstention*).

| Difficulté | Définition |
|---|---|
| facile | une table, un filtre ou un agrégat simple |
| moyen | une jointure, un `GROUP BY`, un classement ou une date |
| difficile | plusieurs jointures, sous-requêtes, auto-jointure, pourcentages |

Les dix catégories (comptage, filtrage, jointures, agrégations, classements, dates, prix,
génériques, avis HAS, ruptures) couvrent toutes les tables de la base ; une onzième,
`hors_perimetre`, regroupe les questions sans réponse.

## Abstention

Un assistant qui invente une requête pour « Quels sont les effets indésirables du LEVOTHYROX ? »
affiche un résultat trompeur : la BDPM ne contient ni effets indésirables, ni posologie, ni ventes,
ni prix étrangers, et elle est en lecture seule. La règle 11 du prompt et un exemple few-shot
apprennent au modèle à répondre `HORS_PERIMETRE` dans ce cas ; le pipeline n'exécute alors aucune
requête et l'interface affiche que la question sort du périmètre.

Les 10 questions hors périmètre couvrent cinq familles : information absente de la base
(posologie, effets indésirables, ventes, chiffre d'affaires, prix en Belgique), sujet voisin mais
autre (pharmacies d'officine), conseil médical personnel, demande de modification, sujet sans
rapport (météo, histoire de la pénicilline). Certaines sont volontairement proches du périmètre :
« Combien de boîtes de DOLIPRANE ont été vendues en 2025 ? » ressemble à une question de comptage.

| Métrique | Définition |
|---|---|
| Abstentions correctes | Questions hors périmètre auxquelles le modèle a répondu `HORS_PERIMETRE`. |
| Abstentions à tort | Questions du périmètre que le modèle a refusées (comptées fausses dans l'exactitude). |

**L'exactitude, l'exécutabilité, les intervalles de confiance et les tests de McNemar portent sur
les seules questions du périmètre**, pour rester comparables aux runs précédents ; l'abstention est
mesurée à part. L'analyse des erreurs ajoute deux causes en tête de liste : abstention manquée et
abstention à tort.

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

## Robustesse à la formulation (runs du 23 octobre 2026, 90 questions)

Configuration par défaut, même jour, même BDPM. Fichiers sources : `results/runs/20261023T*.json`.

| Modèle | Exactitude (90) | IC 95 % | 60 originales | 30 reformulations | Cohérence des paires | Justes conservées |
|---|---:|---:|---:|---:|---:|---:|
| 1.5B | 52,2 % | 42,2 – 62,2 % | 51,7 % | 53,3 % | 83 % (25/30) | 82 % (14/17) |
| 3B | 61,1 % | 51,1 – 71,1 % | 60,0 % | 63,3 % | 87 % (26/30) | 94 % (16/17) |
| 7B | 67,8 % | 57,8 – 76,7 % | 65,0 % | 73,3 % | 90 % (27/30) | 95 % (20/21) |

- Les reformulations ne sont pas plus difficiles que leurs sources : chaque modèle fait aussi bien,
  voire mieux, sur elles. Un modèle qui aurait appris la formulation exacte perdrait au contraire des
  points.
- La robustesse croît avec la taille : le 1.5B perd 3 de ses 17 réponses justes quand la question
  change de mots (q062 « encore sur le marché », q070 « remboursées à 100 % par l'Assurance
  maladie », q078 « relèvent de la liste I ») ; le 7B n'en perd qu'une (q087, écart entre prix TTC et
  prix hors honoraires).
- Les gains inverses (fausse en version d'origine, juste reformulée) montrent qu'une partie des
  erreurs tient aussi à la formulation de la question source : c'est le même bruit, dans l'autre sens.
- Avec 30 paires, ces écarts restent indicatifs.
- **Significativité sur 90 questions.** Le test de McNemar donne pour la première fois un écart
  significatif : 7B contre 1.5B, 23 questions justes pour le 7B seul contre 9 (p = 0,02). 7B contre
  3B (p = 0,24) et 3B contre 1.5B (p = 0,20) ne le sont pas. Prudence : une reformulation n'est pas
  une question indépendante de sa source, le nombre effectif de questions est donc inférieur à 90
  et cette p-valeur est optimiste. Sur les 60 originales seules, l'écart reste non significatif
  (15 contre 7, p = 0,13).

## Abstention et 120 questions (runs du 26 octobre 2026)

Configuration par défaut, même jour, même BDPM. Fichiers sources : `results/runs/20261026T08*.json`
et `20261026T09*.json` (les trois derniers ; un premier passage du matin, sur la version de q098 et
q107 antérieure à leur correction, est conservé pour la traçabilité).

| Modèle | Exactitude (110) | IC 95 % | 80 originales | Abstentions correctes | Abstentions à tort | Cohérence des paires |
|---|---:|---:|---:|---:|---:|---:|
| 1.5B | 50,0 % | 40,9 – 59,1 % | 47,5 % | 7/10 | 8/110 | 73 % |
| 3B | 61,8 % | 52,7 – 70,9 % | 61,2 % | 4/10 | 0/110 | 83 % |
| 7B | 72,7 % | 64,5 – 80,9 % | 71,2 % | **10/10** | 0/110 | 93 % |

- **Le 7B sait s'abstenir, les petits modèles non.** Le 7B refuse les 10 questions hors périmètre sans
  refuser une seule question du périmètre. Le 3B invente une requête pour 6 d'entre elles, y compris
  la demande de suppression (q117, bloquée de toute façon par la garde SQL) et les ventes de
  DOLIPRANE (q113). Le 1.5B s'abstient plus souvent (7/10) mais au hasard : il refuse aussi 8
  questions auxquelles la base répond (q010, q012, q104…), soit 7 points d'exactitude perdus d'office.
- **q113 (boîtes vendues) et q117 (suppression) piègent les deux petits modèles** : la première
  ressemble à un comptage, la seconde à une instruction SQL.
- **Premiers écarts nets.** Sur les 80 questions originales (sans reformulations, donc
  indépendantes), McNemar donne 7B contre 1.5B p < 0,001 (25 contre 6), 3B contre 1.5B p = 0,05 et 7B
  contre 3B p = 0,13. Sur les 110 questions du périmètre, les trois écarts passent sous 5 %
  (p = 0,0001, 0,047 et 0,036), avec la même réserve qu'en S7 sur les reformulations.
- **Les 20 nouvelles questions** (q091 à q110) sont réussies à 16/20 par le 7B. Ses quatre erreurs
  sont de vraies erreurs de raisonnement : groupe générique restreint aux génériques (q097),
  princeps au lieu de groupes (q108), « remise à disposition » confondue avec « tension » (q109),
  plus q107 (conditions de prescription), manquée par les trois modèles.
- **Exactitude stricte** : 59,1 % pour le 7B, 13,6 points sous l'exactitude souple, surtout par
  des colonnes ajoutées (un compte affiché avec l'année demandée, q110).
- Causes d'erreur du 7B : jointures (10), agrégats (7), filtres texte (4), table manquante (4) ;
  aucun SQL invalide.

**Deux questions corrigées après un premier run.** q107 comptait les informations de sécurité
importantes, fichier publié vide par l'ANSM : la référence renvoyait 0 et `check-questions` l'a
signalée ; elle a été remplacée. q098 admettait deux lectures (liens recensés, ou avis SMR reliés à
un lien) ; elle nomme désormais les liens. Les chiffres ci-dessus viennent du second run.

## Comparaison des familles (runs du 28 octobre 2026)

Configuration par défaut, même prompt, même jour, même BDPM, chaque modèle sur son propre runner
(4 cœurs, sans GPU), quantifié en 4 bits par Ollama. Fichiers sources : `results/runs/20261028T*.json`.

| Modèle | Spécialité | Exactitude (110) | IC 95 % | Abstentions correctes | Cohérence des paires | Latence p50 | p95 |
|---|---|---:|---:|---:|---:|---:|---:|
| Qwen2.5-Coder 7B | code | **71,8 %** | 63,6 – 80,0 % | 10/10 | 93 % | 12,5 s | 34,0 s |
| Llama 3.1 8B | généraliste | 59,1 % | 50,0 – 68,2 % | 9/10 | 70 % | 15,7 s | 33,8 s |
| Mistral 7B | généraliste | 47,3 % | 38,2 – 56,4 % | 1/10 | 73 % | 11,5 s | 117,2 s |
| SQLCoder 7B | SQL | 1,8 % | 0,0 – 4,5 % | 4/10 (25 à tort) | — | 127,1 s | 256,6 s |
| Gemma 2 9B | généraliste | non mesuré (aucune réponse en moins de 180 s) | — | — | — | > 180 s | — |

- **À taille égale, le modèle de code l'emporte nettement.** Qwen2.5-Coder 7B devance Llama 3.1 8B
  de 12,7 points (24 questions justes pour Qwen seul contre 10, p = 0,02 sur 110 questions, 0,09 sur
  les 80 originales) et Mistral 7B de 24,5 points (p < 0,001 dans les deux cas). Le Qwen 7B du jour
  (71,8 %) confirme celui du 26 octobre (72,7 %) à une question près.
- **Les généralistes échouent surtout sur les jointures** : 22 erreurs de jointure pour Llama, 26 pour
  Mistral, contre 10 pour Qwen.
- **Savoir s'abstenir dépend de la famille, pas seulement de la taille.** Llama s'abstient sur 9
  des 10 questions hors périmètre sans refus à tort ; Mistral invente une requête pour 9 d'entre
  elles. Mistral est aussi le moins robuste aux reformulations et le plus instable en latence
  (p95 de 117 s, tiré par les questions où une première requête échoue et passe par l'auto-correction).
- **SQLCoder 7B n'est pas comparable dans ce protocole.** C'est un modèle de complétion entraîné
  sur un gabarit de prompt qui lui est propre : en conversation, il ne s'arrête jamais (512 tokens,
  le plafond, à chaque question), recopie les exemples few-shot (filtre `BIOGARAN` sur des questions
  qui n'en parlent pas) et dépasse le délai de 180 s sur certaines questions. Son 1,8 % mesure
  l'inadéquation du format, pas sa compétence en SQL ; l'évaluer équitablement demanderait son
  gabarit dédié, hors du protocole commun.
- **Gemma 2 9B ne tient pas sur un runner sans GPU.** Au premier essai, il a atteint la limite de
  5 h 40 du runner. Relancé seul, il a dépassé le délai de 180 s à chacune des 90 premières
  questions, soit une question toutes les trois minutes, sans une seule réponse. Les autres modèles
  de cette taille répondent en 12 à 16 s (médiane), parce qu'Ollama réutilise d'une question à
  l'autre le calcul du long préfixe commun (règles, schéma, exemples, environ 3 000 tokens). Cause
  probable, non vérifiée : l'attention à fenêtre glissante de Gemma 2 empêche cette réutilisation,
  et le préfixe est recalculé à chaque appel. Gemma 2 est donc exclu de la comparaison sur CPU ;
  il reste évaluable sur une machine avec GPU (`medsql eval --model gemma2:9b`).

## Limites connues

- 110 questions du périmètre donnent encore un intervalle de confiance à 95 % d'environ ±8 points ;
  deux modèles proches restent difficiles à départager (voir *Incertitude et significativité*).
- 10 questions hors périmètre suffisent à montrer l'écart entre le 7B et les petits modèles, pas à
  estimer finement un taux d'abstention (une question vaut 10 points).
- La table `informations_importantes` est vide dans la BDPM actuelle : aucune question n'y fait appel.
- Les questions ont été rédigées par l'auteur du projet, avec un biais possible vers des
  formulations proches du schéma.
- Une question ambiguë peut admettre plusieurs requêtes correctes ; la référence en retient une.
