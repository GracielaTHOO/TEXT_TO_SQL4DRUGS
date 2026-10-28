# Journal des modifications

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), versionnage [SemVer](https://semver.org/lang/fr/).

## [Non publié]

### Ajouté
- Comparaison multi-familles : catalogue des modèles (`medsql.models` : famille, éditeur, taille, spécialité, licence) et section *Familles de modèles* du tableau de bord.
- Évaluation interruptible : sur Ctrl+C ou arrêt du runner, `medsql eval` enregistre les réponses obtenues dans un run partiel (`interrupted`, hors classement) ; l'étape d'évaluation du workflow a son propre délai pour que l'envoi des résultats s'exécute.
- Workflow d'évaluation en matrice : un runner par modèle, en parallèle, puis le workflow réutilisable *Publication des résultats* (`publish.yml`), exécuté même si un modèle échoue et lançable à la main sur les artefacts d'une évaluation passée.
- Abstention : règle 11 du prompt et exemple few-shot `HORS_PERIMETRE` ; le pipeline n'exécute aucune requête quand le modèle juge la question hors du périmètre de la base (`Answer.abstained`), la CLI et la démo l'affichent.
- Jeu porté à 120 questions : 20 nouvelles questions du périmètre (q091 à q110) et 10 questions hors périmètre (q111 à q120, champ `hors_perimetre`) dont la seule réponse juste est l'abstention.
- Mesure de l'abstention (`medsql.eval.abstention`) : abstentions correctes et à tort dans le résumé des runs, colonne *Abstention* du README, section *Savoir s'abstenir* du tableau de bord, deux nouvelles causes dans l'analyse des erreurs.
- Jeu porté à 90 questions : 30 reformulations (q061 à q090, champ `paraphrase_de`) qui héritent de la requête de référence de leur source.
- Robustesse à la formulation (`medsql.eval.robustness`) : cohérence des paires et part des réponses justes conservées, dans le résumé des runs et le tableau de bord.
- Intervalles de confiance à 95 % par bootstrap (`medsql.eval.significance`) dans le README, le classement et le graphique du tableau de bord (moustaches).
- Test exact de McNemar apparié : comparaison des modèles deux à deux (section *Les écarts sont-ils réels ?*) et p-valeur de chaque ablation.

### Modifié
- Au-delà de quatre modèles, la section *Les écarts sont-ils réels ?* compare chaque modèle au meilleur au lieu de toutes les paires.
- L'exactitude, l'exécutabilité, les intervalles de confiance et les tests de McNemar ne portent que sur les questions du périmètre.
- Questions q098 (liens vers les avis) et q107 (remplacée : la table des informations importantes est publiée vide) corrigées après le premier run de S8.
- Question q057 précisée : « déclarations de rupture de stock », ce que compte la requête de référence.

### Résultats
- Familles (28 octobre 2026), exactitude sur 110 questions : Qwen2.5-Coder 7B 71,8 %, Llama 3.1 8B 59,1 % (p = 0,02 contre Qwen), Mistral 7B 47,3 % (p < 0,001), SQLCoder 7B 1,8 % (modèle de complétion, inadapté au format conversationnel). Abstentions correctes : 10, 9, 1 et 4 sur 10.
- 120 questions (26 octobre 2026), exactitude sur les 110 du périmètre : 7B 72,7 %, 3B 61,8 %, 1.5B 50,0 %. Abstentions correctes : 10/10, 4/10 et 7/10 ; abstentions à tort : 0, 0 et 8. Sur les 80 questions originales, 7B contre 1.5B p < 0,001.
- 90 questions (23 octobre 2026) : 7B 67,8 %, 3B 61,1 %, 1.5B 52,2 %. Cohérence des paires source et reformulation : 90 %, 87 % et 83 %. Premier écart significatif, 7B contre 1.5B (p = 0,02, optimiste car les reformulations ne sont pas indépendantes ; p = 0,13 sur les 60 originales).
- Aucun écart n'est significatif sur 60 questions, pas même Qwen2.5-Coder 7B contre 1.5B (p = 0,26). Puissance estimée : 42 % à 120 questions, 84 % à 300.

## [0.2.0] - 2026-10-19

Premiers chiffres réels sur la BDPM, ablations, analyse d'erreurs et démo Docker autonome.

### Résultats
- Configuration par défaut (libellés exacts, few-shot, une auto-correction), 60 questions : Qwen2.5-Coder 7B 68,3 %, 3B 60,0 %, 1.5B 58,3 %. Jointures et agrégats concentrent 30 des 68 erreurs.
- Premiers runs complets sur la BDPM réelle (12 octobre 2026, 60 questions) : Qwen2.5-Coder 7B 60,0 %, 3B 56,7 %, 1.5B 56,7 %. Détail et constats dans `docs/evaluation.md`.
- Ablations du 14 octobre 2026 : les libellés exacts font gagner 5,0 points au 7B (68,3 %) et 3,3 points au 1.5B ; sans exemples, le 1.5B perd 6,7 points ; sans auto-correction, 1,7 à 3,3 points.

### Ajouté
- Workflow *Image Docker de la démo* : construction de l'image, démarrage et question réelle au modèle embarqué à chaque push qui touche le code. `scripts/stage_demo.py` assemble le contexte de construction pour un lancement en local.
- Analyse automatique des erreurs (`medsql.eval.errors`) : chaque réponse fausse reçoit une cause (pas de réponse du modèle, SQL invalide, table manquante, jointure, agrégat, filtre texte, lignes en trop ou en moins, valeurs) par comparaison avec la requête de référence. Section *Analyse des erreurs* du tableau de bord, applicable aussi aux runs anciens.
- Ablations : option `--value-hints/--no-value-hints` (libellés exacts des colonnes catégorielles dans le prompt), entrée `configs` du workflow d'évaluation (`base`, `zero-shot`, `sans-correction`, `sans-libelles`) et section *Ablations* du tableau de bord : effet de chaque facteur retiré seul, par rapport au run qui ne diffère que par ce facteur.
- Workflow *Tableau de bord (GitHub Pages)* : publie `results/dashboard.html` sans relancer l'évaluation.
- `medsql profile` : profil de la base réelle (volumétrie, complétude, plages de dates, valeurs fréquentes) publié dans `docs/donnees-profil.md`.
- `medsql check-questions` : exécution des requêtes de référence sur la base réelle et liste des questions à revoir (`results/questions_check.json`).
- Variable `MEDSQL_MAX_TOKENS` (512 par défaut) : plafond de génération transmis à Ollama (`num_predict`) et aux API compatibles OpenAI (`max_tokens`).

### Modifié
- La démo n'est plus publiée sur Hugging Face Spaces : elle se lance en local depuis l'image Docker autonome (`docker/`, ex-`space/`). Le workflow de déploiement et le secret `HF_TOKEN` ne servent plus.
- Les libellés exacts sont désormais inclus par défaut dans le prompt (CLI, démo et évaluation), après le gain mesuré en S3. Les runs antérieurs, faits sans eux, sont étiquetés « sans libellés exacts ».

### Corrigé
- Démo : une seule question traitée à la fois. Deux questions simultanées partageaient la connexion SQLite et pouvaient écraser le délai d'exécution l'une de l'autre.
- Un délai dépassé ou une panne du serveur LLM n'interrompt plus l'évaluation : la question est comptée fausse avec l'erreur `LLMError`, et le banc continue (constaté sur le premier run réel, bloqué à la 10e question).
- Une requête générée avec une chaîne non fermée (`TokenError` de sqlglot) est désormais refusée proprement puis réparée, au lieu d'interrompre l'évaluation ; toute autre erreur inattendue sur une question est enregistrée sans arrêter le banc.
- Question q021 : sa référence renvoyait 0 ligne sur la BDPM réelle (DOLIPRANE absent du répertoire des génériques). Elle porte désormais sur TAHOR 10 mg (15 génériques).
- Question q041 : aucune spécialité à base d'amoxicilline n'est en rupture ni en tension dans la BDPM du 9 octobre 2026. Elle compte désormais les substances actives des spécialités commercialisées en rupture ou en tension.
- Question q058 : le fichier `CIS_InfoImportantes.txt` est publié vide par l'ANSM (0 octet le 9 octobre 2026), la table `informations_importantes` aussi. La question porte désormais sur les ruptures et tensions commencées depuis le 1er janvier 2026, sans dépendre de `date('now')`.
- `medsql check-questions` signale réellement les réponses dégénérées (une seule ligne de valeurs nulles ou `NULL`, par exemple un `COUNT` sur une table vide) : le champ existait mais n'était jamais renseigné.
- Le workflow d'évaluation enregistre les résultats partiels même si un modèle échoue.
- Tableau de bord public sur GitHub Pages (dépôt passé en public le 13 octobre 2026) ; un échec de publication fait de nouveau échouer le workflow.

## [0.1.0] - 2026-10-07

### Ajouté
- Chargement des 11 fichiers de la BDPM dans une base SQLite normalisée (12 tables, index, types).
- Normalisation des formats ANSM : encodages, trois formats de date, prix à séparateur de milliers, taux.
- Garde-fous SQL en trois couches : analyse sqlglot, connexion en lecture seule, autorisateur SQLite ; délai et plafond de lignes.
- Clients LLM Ollama et compatible OpenAI (vLLM, llama.cpp, LM Studio).
- Prompt avec schéma annoté, règles métier et exemples few-shot ; auto-correction sur erreur SQL.
- Jeu d'évaluation de 60 questions (3 niveaux, 10 catégories) et métrique d'exactitude par exécution.
- CLI `medsql` : `setup`, `ask`, `eval`, `report`, `stats`, `docs`.
- Tableau de bord HTML autonome et tableau de résultats du README générés automatiquement.
- Démo Gradio et image Docker pour Hugging Face Spaces.
- CI (ruff, mypy strict, pytest sur Python 3.10 à 3.13), workflow d'évaluation mensuel, déploiement du Space.
