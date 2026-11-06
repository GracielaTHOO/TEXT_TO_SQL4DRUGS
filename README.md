<div align="center">

<img src="assets/logo.svg" width="96" alt="">

# Text-to-SQL médicaments

**Posez une question en français, un LLM local la traduit en SQL sur la Base de données publique des médicaments.**
**Chaque modèle est mesuré sur un jeu de 120 questions de référence, dont 30 reformulations et 10 questions hors périmètre auxquelles il doit refuser de répondre.**

[![CI](https://github.com/GracielaTHOO/TEXT_TO_SQL4DRUGS/actions/workflows/ci.yml/badge.svg)](https://github.com/GracielaTHOO/TEXT_TO_SQL4DRUGS/actions/workflows/ci.yml)
[![Évaluation](https://github.com/GracielaTHOO/TEXT_TO_SQL4DRUGS/actions/workflows/eval.yml/badge.svg)](https://github.com/GracielaTHOO/TEXT_TO_SQL4DRUGS/actions/workflows/eval.yml)
![Python](https://img.shields.io/badge/python-3.11%20%E2%86%92%203.13-2a78d6)
![Typage](https://img.shields.io/badge/mypy-strict-2a78d6)
![Licence](https://img.shields.io/badge/licence-MIT-2a78d6)
[![Tableau de bord](https://img.shields.io/badge/%F0%9F%93%88%20tableau%20de%20bord-GitHub%20Pages-2a78d6)](https://gracielathoo.github.io/TEXT_TO_SQL4DRUGS/)

</div>

---

```text
$ medsql ask "Quelles substances actives sont le plus souvent en rupture ou en tension ?"

SELECT c.substance, COUNT(DISTINCT d.cis) AS nb_specialites
FROM disponibilites d
JOIN compositions c ON c.cis = d.cis
WHERE d.code_statut IN (1, 2) AND c.nature_composant = 'SA'
GROUP BY c.substance
ORDER BY nb_specialites DESC
LIMIT 10
```

## 🎯 En bref

| | |
|---|---|
| 📦 **Données** | Les 11 fichiers open data de la [BDPM](https://base-donnees-publique.medicaments.gouv.fr/telechargement) (ANSM, HAS, Assurance maladie), normalisés en 12 tables SQLite documentées |
| 🧠 **Modèles** | LLM locaux servis par [Ollama](https://ollama.com) ou toute API compatible OpenAI ([vLLM](https://docs.vllm.ai), llama.cpp) |
| 🧪 **Évaluation** | 120 questions en français (80 + 30 reformulations + 10 hors périmètre), 3 niveaux, 10 catégories, exactitude mesurée par exécution, robustesse à la formulation, abstention |
| 🛡️ **Sécurité** | SQL en lecture seule garanti par trois barrières indépendantes |
| 🖥️ **Interfaces** | CLI `medsql`, démo Gradio (réponse rédigée en français, export CSV, historique ; aussi en image Docker autonome), tableau de bord HTML |
| ✅ **Qualité** | 350+ tests, mypy strict, ruff, CI sur Python 3.11 à 3.13 |

## 📊 Résultats

<!-- RESULTS:START -->
| Modèle | Exactitude | IC 95 % | Exactitude stricte | SQL exécutable | Abstention | Latence p50 | Latence p95 | Date |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| qwen2.5-coder:7b · exemples dynamiques (nomic-embed-text) | **79,1 %** | 70,9 – 86,4 % | 62,7 % | 100,0 % | 8/10 | 27,2 s | 47,9 s | 2026-11-04 |
| qwen2.5-coder:7b · exemples dynamiques (lexical) | **74,5 %** | 66,4 – 82,7 % | 59,1 % | 99,1 % | 8/10 | 31,0 s | 45,0 s | 2026-10-30 |
| qwen2.5-coder:7b | **70,9 %** | 62,7 – 79,1 % | 57,3 % | 99,1 % | 10/10 | 12,4 s | 33,6 s | 2026-11-04 |
| qwen2.5-coder:3b · exemples dynamiques (nomic-embed-text) | **69,1 %** | 60,9 – 77,3 % | 54,5 % | 98,2 % | 2/10 | 13,6 s | 30,9 s | 2026-11-04 |
| qwen2.5-coder:3b · exemples dynamiques (lexical) | **64,5 %** | 55,5 – 73,6 % | 49,1 % | 95,5 % | 1/10 | 14,3 s | 25,0 s | 2026-10-30 |
| qwen2.5-coder:7b · sans libellés exacts | **63,3 %** | 51,7 – 75,0 % | 51,7 % | 100,0 % | – | 14,7 s | 36,9 s | 2026-10-14 |
| qwen2.5-coder:7b · zero-shot · sans libellés exacts | **63,3 %** | 51,7 – 75,0 % | 50,0 % | 100,0 % | – | 14,0 s | 24,9 s | 2026-10-14 |
| qwen2.5-coder:3b | **61,8 %** | 52,7 – 70,9 % | 47,3 % | 90,9 % | 4/10 | 8,0 s | 28,3 s | 2026-11-04 |
| qwen2.5-coder:7b · sans auto-correction · sans libellés exacts | **61,7 %** | 48,3 – 73,3 % | 50,0 % | 95,0 % | – | 15,2 s | 27,3 s | 2026-10-14 |
| qwen2.5-coder:1.5b · exemples dynamiques (nomic-embed-text) | **60,0 %** | 50,9 – 69,1 % | 49,1 % | 91,8 % | 2/10 | 5,0 s | 9,7 s | 2026-11-04 |
| llama3.1:8b | **59,1 %** | 50,0 – 68,2 % | 45,5 % | 98,2 % | 9/10 | 15,7 s | 33,8 s | 2026-10-28 |
| qwen2.5-coder:3b · sans libellés exacts | **56,7 %** | 43,3 – 68,3 % | 41,7 % | 91,7 % | – | 7,4 s | 25,2 s | 2026-10-12 |
| qwen2.5-coder:1.5b · sans libellés exacts | **55,0 %** | 41,7 – 66,7 % | 33,3 % | 95,0 % | – | 3,8 s | 11,1 s | 2026-10-14 |
| qwen2.5-coder:1.5b · exemples dynamiques (lexical) | **54,5 %** | 45,5 – 63,6 % | 40,0 % | 93,6 % | 4/10 | 3,2 s | 6,1 s | 2026-10-30 |
| qwen2.5-coder:1.5b · sans auto-correction · sans libellés exacts | **51,7 %** | 38,3 – 65,0 % | 33,3 % | 88,3 % | – | 3,6 s | 5,8 s | 2026-10-14 |
| qwen2.5-coder:1.5b | **50,9 %** | 41,8 – 60,0 % | 38,2 % | 82,7 % | 7/10 | 2,6 s | 8,1 s | 2026-11-04 |
| qwen2.5-coder:1.5b · zero-shot · sans libellés exacts | **48,3 %** | 35,0 – 61,7 % | 41,7 % | 91,7 % | – | 3,4 s | 8,6 s | 2026-10-14 |
| mistral:7b | **47,3 %** | 38,2 – 56,4 % | 37,3 % | 92,7 % | 1/10 | 11,5 s | 117,2 s | 2026-10-28 |
| sqlcoder:7b | **1,8 %** | 0,0 – 4,5 % | 1,8 % | 70,0 % | 4/10 | 127,1 s | 256,6 s | 2026-10-28 |

_110 questions + 10 hors périmètre · exactitude = résultat d'exécution identique à la référence, sur les questions du périmètre · abstention = questions hors périmètre correctement refusées · IC 95 % par bootstrap sur les questions (voir [docs/evaluation.md](docs/evaluation.md))._
<!-- RESULTS:END -->

Ce tableau est régénéré par `medsql report` à chaque évaluation. Le détail par difficulté,
par catégorie et question par question est dans le [tableau de bord](https://gracielathoo.github.io/TEXT_TO_SQL4DRUGS/).

## ⚙️ Fonctionnement

```mermaid
flowchart LR
    Q["💬 Question"] --> P["📝 Prompt<br/>schéma annoté<br/>+ règles métier<br/>+ 3 exemples"]
    P --> L["🧠 LLM local"]
    L --> G{"🛡️ Garde-fous"}
    G -- refus --> E["⛔ Erreur"]
    G -- OK --> S[("🗄️ SQLite<br/>lecture seule")]
    S -- erreur SQL --> P
    S --> R["📋 Résultat"]
```

1. **Prompt** : le schéma complet, annoté en français, avec les règles propres à la BDPM
   (noms en majuscules accentuées, dates ISO, CIS contre CIP13…).
2. **Génération** : température 0, graine fixe.
3. **Garde-fous** : une seule instruction `SELECT` vérifiée par [sqlglot](https://github.com/tobymao/sqlglot),
   base ouverte en lecture seule, autorisateur SQLite qui refuse toute écriture, délai maximal de 10 s.
4. **Auto-correction** : en cas d'erreur SQL, le modèle reçoit le message d'erreur et a droit à un second essai.

## 🚀 Démarrage rapide

```bash
git clone https://github.com/GracielaTHOO/TEXT_TO_SQL4DRUGS.git
cd TEXT_TO_SQL4DRUGS
pip install -e ".[app]"

medsql setup                       # télécharge la BDPM et construit data/bdpm.sqlite
ollama pull qwen2.5-coder:7b       # https://ollama.com/download
medsql ask "Combien de médicaments sont sous surveillance renforcée ?"
python app/app.py                  # démo sur http://127.0.0.1:7860
```

Sans rien installer d'autre que Docker : `python scripts/stage_demo.py --out build/demo`, puis
`docker build -t medsql-demo build/demo` et `docker run -p 7860:7860 medsql-demo`.

## 🧰 Commandes

| Commande | Rôle |
|---|---|
| `medsql setup` | Télécharge la BDPM puis construit la base |
| `medsql stats` | Affiche les chiffres clés de la base |
| `medsql ask "…"` | Pose une question, affiche le SQL et le résultat |
| `medsql eval --model …` | Évalue un modèle sur les 120 questions |
| `medsql redteam --model …` | Passe les 28 questions adverses ; échoue en cas d'incident ([docs/securite.md](docs/securite.md)) |
| `medsql report` | Génère le tableau de bord et met à jour ce README |
| `medsql profile` | Génère le profil de la base réelle ([docs/donnees-profil.md](docs/donnees-profil.md)) |
| `medsql check-questions` | Vérifie les requêtes de référence sur la base réelle |
| `medsql docs` | Régénère le dictionnaire de données |

Options utiles : `--backend vllm --base-url http://localhost:8000`, `--zero-shot`, `--repairs 0`, `--limit 10`.
`make help` liste les raccourcis de développement.

## 🧪 Évaluation

La réponse d'un modèle est **juste** si l'exécution de son SQL renvoie exactement les mêmes lignes
que la requête de référence (colonnes supplémentaires tolérées). Les réponses attendues sont
recalculées sur la base du jour, si bien que le jeu reste valide après chaque mise à jour mensuelle.

| Difficulté | Questions | Exemple |
|---|---:|---|
| Facile | 25 | *Combien de médicaments ne sont plus commercialisés ?* |
| Moyen | 26 | *Quel laboratoire est titulaire du plus grand nombre de génériques ?* |
| Difficile | 9 | *Quels sont les génériques du TAHOR 10 mg ?* |

Méthodologie complète, ablations et limites : [docs/evaluation.md](docs/evaluation.md).

## 🗂️ Organisation du dépôt

```text
├── src/medsql/
│   ├── data/            téléchargement, normalisation, schéma, construction SQLite
│   ├── llm/             clients Ollama et compatible OpenAI
│   ├── eval/            questions.yaml, métriques, banc d'évaluation
│   ├── sql_guard.py     garde-fous d'exécution (voir docs/securite.md)
│   ├── prompting.py     prompt, exemples, auto-correction
│   ├── pipeline.py      question → SQL → résultat
│   ├── report.py        tableau de bord HTML et tableau du README
│   └── cli.py           commande medsql
├── app/app.py           démo Gradio
├── docker/              image Docker autonome de la démo (Ollama embarqué)
├── results/runs/        un fichier JSON par évaluation
├── tests/               146 tests, échantillon synthétique au format BDPM
└── docs/                architecture, données, évaluation, déploiement, feuille de route
```

## 📚 Documentation

- [Architecture et choix de conception](docs/architecture.md)
- [Dictionnaire de données](docs/data.md)
- [Méthodologie d'évaluation](docs/evaluation.md)
- [Déploiement (local, vLLM, Docker, GitHub Pages)](docs/deploiement.md)
- [Sécurité et tests adverses](docs/securite.md)
- [Plan de développement](docs/PLAN.md) · [Feuille de route](docs/roadmap.md)
- [Contribuer](CONTRIBUTING.md) · [Journal des modifications](CHANGELOG.md)

## ⚖️ Données et avertissement

Données : [Base de données publique des médicaments](https://base-donnees-publique.medicaments.gouv.fr),
ANSM, réutilisation libre. Le code est sous licence [MIT](LICENSE).

Ce projet est une démonstration technique. Les réponses générées peuvent être fausses et
**ne constituent pas un avis médical**.
