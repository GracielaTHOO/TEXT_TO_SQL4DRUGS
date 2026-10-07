.PHONY: help install setup test lint format typecheck check eval report app docs fixtures

MODEL ?= qwen2.5-coder:7b

help: ## Affiche cette aide
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[36m%-11s\033[0m %s\n", $$1, $$2}'

install: ## Installe le projet en mode développement
	pip install -e ".[dev,app]"

setup: ## Télécharge la BDPM et construit la base SQLite
	medsql setup

test: ## Lance les tests avec couverture
	pytest --cov --cov-report=term-missing

lint: ## Vérifie le style (ruff)
	ruff check . && ruff format --check .

format: ## Formate le code (ruff)
	ruff check --fix . && ruff format .

typecheck: ## Vérifie les types (mypy strict)
	mypy

check: lint typecheck test ## Lint + typage + tests (comme la CI)

eval: ## Évalue un modèle : make eval MODEL=qwen2.5-coder:7b
	ollama pull $(MODEL) && medsql eval --model $(MODEL)

report: ## Génère le tableau de bord et met à jour le README
	medsql report

app: ## Lance la démo Gradio en local
	python app/app.py

docs: ## Régénère docs/data.md depuis le schéma
	medsql docs

fixtures: ## Régénère l'échantillon de test
	python scripts/make_fixtures.py
