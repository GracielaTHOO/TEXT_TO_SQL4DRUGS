#!/usr/bin/env bash
# Démarre Ollama puis la démo Gradio (point d'entrée du Space).
set -euo pipefail

ollama serve > /tmp/ollama.log 2>&1 &
for _ in $(seq 1 60); do
  curl -sf http://127.0.0.1:11434/api/tags > /dev/null && break
  sleep 1
done

# Préchauffage : charge le modèle et met en cache le préfixe du prompt (schéma + exemples).
medsql ask "Combien de spécialités sont commercialisées ?" > /dev/null 2>&1 || true

exec python app/app.py
