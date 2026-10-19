# Déploiement

## En local

```bash
pip install -e ".[app]"
medsql setup                      # BDPM → data/bdpm.sqlite
ollama pull qwen2.5-coder:7b
python app/app.py                 # http://127.0.0.1:7860
```

Variables d'environnement (préfixe `MEDSQL_`) :

| Variable | Défaut | Rôle |
|---|---|---|
| `MEDSQL_BACKEND` | `ollama` | `ollama`, `openai`, `vllm` ou `llamacpp` |
| `MEDSQL_MODEL` | `qwen2.5-coder:7b` | nom du modèle côté serveur |
| `MEDSQL_BASE_URL` | `http://localhost:11434` | URL du serveur LLM |
| `MEDSQL_API_KEY` | vide | clé éventuelle (API compatible OpenAI) |
| `MEDSQL_DATA_DIR` | `data` | dossier des fichiers bruts et de la base |
| `MEDSQL_MAX_TOKENS` | `512` | tokens générés au maximum par réponse |
| `MEDSQL_MAX_ROWS` | `200` | lignes maximum affichées |
| `MEDSQL_QUERY_TIMEOUT` | `10` | délai maximal d'une requête SQL (s) |

### Avec vLLM

```bash
vllm serve Qwen/Qwen2.5-Coder-7B-Instruct --port 8000
MEDSQL_BACKEND=vllm MEDSQL_BASE_URL=http://localhost:8000 \
  medsql eval --model Qwen/Qwen2.5-Coder-7B-Instruct
```

## Hugging Face Spaces

Le dossier `space/` contient une image Docker qui embarque Ollama, le modèle et la base :

1. créer un jeton d'écriture sur https://huggingface.co/settings/tokens ;
2. l'ajouter au dépôt GitHub : *Settings → Secrets and variables → Actions → New secret*,
   nom `HF_TOKEN` ;
3. (facultatif) définir la variable `HF_SPACE` si le Space ne s'appelle pas
   `GracielaTHOO/text2sql-medicaments` ;
4. chaque push sur `main` qui touche le code publie le Space (workflow *Déploiement Hugging Face Space*).

Avant toute publication, le même workflow construit l'image sur le runner GitHub, la démarre et pose
une vraie question au modèle embarqué (`medsql ask`). Ce test tourne aussi sans jeton : une image
cassée est repérée avant d'atteindre le Space. Pour assembler le Space en local sans le publier :
`python scripts/deploy_space.py --out build/space`, puis `docker build build/space`.

Le Space gratuit (2 vCPU, 16 Go) utilise `qwen2.5-coder:1.5b` : la première question prend
une trentaine de secondes (chargement du modèle et du schéma), les suivantes quelques secondes.
Pour un modèle plus gros, changer `MEDSQL_MODEL` dans le Dockerfile et passer sur un matériel payant.

## GitHub Pages (tableau de bord)

En ligne sur <https://gracielathoo.github.io/TEXT_TO_SQL4DRUGS/> (dépôt public, *Settings → Pages →
Source : GitHub Actions*). Le workflow *Évaluation des modèles* publie `results/dashboard.html` à chaque
run ; le workflow *Tableau de bord (GitHub Pages)* le republie seul, à la demande ou quand le fichier
change sur `main`.

## Évaluation automatique

Le workflow *Évaluation des modèles* tourne le 2 de chaque mois (après la mise à jour de la BDPM)
et à la demande. Il évalue les modèles sur CPU, enregistre les runs dans `results/runs/`,
met à jour le README et republie le tableau de bord.
