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

## Démo dans Docker

Le dossier `docker/` contient une image autonome qui embarque Ollama, `qwen2.5-coder:1.5b`, la base
BDPM et la démo Gradio. Rien d'autre à installer que Docker :

```bash
python scripts/stage_demo.py --out build/demo
docker build -t medsql-demo build/demo     # télécharge la BDPM et le modèle (~1 Go)
docker run -p 7860:7860 medsql-demo        # http://127.0.0.1:7860
```

À chaque push qui touche le code, le workflow *Image Docker de la démo* construit l'image sur le
runner GitHub, la démarre et pose une vraie question au modèle embarqué (`medsql ask`). L'image
n'est publiée sur aucun registre ni hébergeur : la démo se lance en local.

Sur 2 vCPU, la première question prend une trentaine de secondes (chargement du modèle et du
schéma), les suivantes quelques secondes. Pour un modèle plus gros, construire avec
`--build-arg MEDSQL_MODEL=qwen2.5-coder:7b`.

## GitHub Pages (tableau de bord)

En ligne sur <https://gracielathoo.github.io/TEXT_TO_SQL4DRUGS/> (dépôt public, *Settings → Pages →
Source : GitHub Actions*). Le workflow *Évaluation des modèles* publie `results/dashboard.html` à chaque
run ; le workflow *Tableau de bord (GitHub Pages)* le republie seul, à la demande ou quand le fichier
change sur `main`.

## Évaluation automatique

Le workflow *Évaluation des modèles* tourne le 2 de chaque mois (après la mise à jour de la BDPM)
et à la demande. Chaque modèle de l'entrée `models` a son propre runner (CPU) : les modèles sont
évalués en parallèle, chacun sur la BDPM téléchargée le jour même. Le workflow *Publication des résultats*
(`publish.yml`), appelé à la fin même si un modèle échoue, rassemble les runs dans `results/runs/`,
contrôle les questions, met à jour le README et republie le tableau de bord. Il se lance aussi à la
main pour republier les artefacts d'une évaluation passée : `gh workflow run publish.yml -f run_id=…`.
Un modèle trop lent est arrêté au bout de 300 minutes ; ses réponses déjà obtenues sont
enregistrées dans un run partiel, hors classement.
Exemple pour comparer cinq familles en une fois :
`gh workflow run eval.yml -f models=qwen2.5-coder:7b,llama3.1:8b,mistral:7b,gemma2:9b,sqlcoder:7b`.
