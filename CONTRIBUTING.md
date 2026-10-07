# Contribuer

## Mise en place

```bash
python -m venv .venv && source .venv/bin/activate
make install        # dépendances de développement et de la démo
make setup          # télécharge la BDPM et construit data/bdpm.sqlite
make check          # ruff + mypy strict + pytest : doit passer avant tout commit
```

## Conventions

- **Commits** : [Conventional Commits](https://www.conventionalcommits.org/fr/) en français
  (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `eval:`, `chore:`).
- **Code** : typé (mypy strict), formaté par `ruff format`, docstrings en français.
- **Schéma** : toute modification de `src/medsql/data/schema.py` s'accompagne de `make docs`.
- **Jeu d'évaluation** : une nouvelle question doit
  1. avoir une requête de référence qui ne renvoie pas un résultat vide sur la base réelle ;
  2. ne pas reprendre un exemple few-shot du prompt (vérifié par `tests/test_dataset.py`) ;
  3. utiliser `sans_accents()` pour toute recherche textuelle.
- **Résultats** : on ne modifie jamais un fichier de `results/runs/` à la main.

## Ajouter un modèle au classement

```bash
ollama pull <modele>
medsql eval --model <modele>
medsql report
```

Ou depuis GitHub : *Actions → Évaluation des modèles → Run workflow*.
