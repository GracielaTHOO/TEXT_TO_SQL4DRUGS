# Journal des modifications

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), versionnage [SemVer](https://semver.org/lang/fr/).

## [Non publié]

### Ajouté
- `medsql profile` : profil de la base réelle (volumétrie, complétude, plages de dates, valeurs fréquentes) publié dans `docs/donnees-profil.md`.
- `medsql check-questions` : exécution des requêtes de référence sur la base réelle et liste des questions à revoir (`results/questions_check.json`).
- Variable `MEDSQL_MAX_TOKENS` (512 par défaut) : plafond de génération transmis à Ollama (`num_predict`) et aux API compatibles OpenAI (`max_tokens`).

### Corrigé
- Un délai dépassé ou une panne du serveur LLM n'interrompt plus l'évaluation : la question est comptée fausse avec l'erreur `LLMError`, et le banc continue (constaté sur le premier run réel, bloqué à la 10e question).
- Une requête générée avec une chaîne non fermée (`TokenError` de sqlglot) est désormais refusée proprement puis réparée, au lieu d'interrompre l'évaluation ; toute autre erreur inattendue sur une question est enregistrée sans arrêter le banc.
- Question q021 : sa référence renvoyait 0 ligne sur la BDPM réelle (DOLIPRANE absent du répertoire des génériques). Elle porte désormais sur TAHOR 10 mg (15 génériques).
- Question q041 : aucune spécialité à base d'amoxicilline n'est en rupture ni en tension dans la BDPM du 9 octobre 2026. Elle compte désormais les substances actives des spécialités commercialisées en rupture ou en tension.
- Question q058 : le fichier `CIS_InfoImportantes.txt` est publié vide par l'ANSM (0 octet le 9 octobre 2026), la table `informations_importantes` aussi. La question porte désormais sur les ruptures et tensions commencées depuis le 1er janvier 2026, sans dépendre de `date('now')`.
- `medsql check-questions` signale réellement les réponses dégénérées (une seule ligne de valeurs nulles ou `NULL`, par exemple un `COUNT` sur une table vide) : le champ existait mais n'était jamais renseigné.
- Le workflow d'évaluation enregistre les résultats partiels même si un modèle échoue, et ne bloque plus tant que GitHub Pages n'est pas activé.

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
