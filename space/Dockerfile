# Image Hugging Face Spaces (SDK Docker) : Ollama + base BDPM + démo Gradio.
# Le modèle et la base sont préparés au build : le Space démarre en quelques secondes.
FROM python:3.11-slim

ARG MEDSQL_MODEL=qwen2.5-coder:1.5b
ENV MEDSQL_MODEL=${MEDSQL_MODEL} \
    MEDSQL_BACKEND=ollama \
    MEDSQL_BASE_URL=http://127.0.0.1:11434 \
    MEDSQL_DATA_DIR=/home/user/app/data \
    GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates zstd \
    && curl -fsSL https://ollama.com/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face exécute le conteneur avec l'UID 1000.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    OLLAMA_MODELS=/home/user/.ollama/models
WORKDIR /home/user/app

COPY --chown=user . .
RUN pip install --no-cache-dir --user ".[app]"

# Téléchargement de la BDPM et construction de la base SQLite.
RUN medsql setup

# Pré-chargement des poids du modèle dans l'image.
RUN (ollama serve > /tmp/ollama.log 2>&1 &) \
    && for i in $(seq 1 30); do curl -sf http://127.0.0.1:11434/api/tags > /dev/null && break; sleep 1; done \
    && ollama pull "${MEDSQL_MODEL}"

EXPOSE 7860
CMD ["bash", "start.sh"]
