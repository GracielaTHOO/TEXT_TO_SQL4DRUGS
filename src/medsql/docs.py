"""Génération du dictionnaire de données (``docs/data.md``) depuis le schéma."""

from __future__ import annotations

from medsql.data.schema import TABLES

HEADER = """# Dictionnaire de données

> Fichier généré par `medsql docs` à partir de `src/medsql/data/schema.py`. Ne pas éditer à la main.

Source : [Base de données publique des médicaments](https://base-donnees-publique.medicaments.gouv.fr/telechargement)
(ANSM, HAS, Assurance maladie), mise à jour mensuelle, réutilisation libre.

## Modèle relationnel

```mermaid
erDiagram
    medicaments ||--o{ medicament_voies : "s'administre par"
    medicaments ||--o{ presentations : "est vendu en"
    medicaments ||--o{ compositions : contient
    medicaments ||--o{ groupes_generiques : "appartient à"
    medicaments ||--o{ avis_smr : "évalué (SMR)"
    medicaments ||--o{ avis_asmr : "évalué (ASMR)"
    medicaments ||--o{ conditions_prescription : "soumis à"
    medicaments ||--o{ disponibilites : "signalé en"
    medicaments ||--o| mitm : "classé"
    medicaments ||--o{ informations_importantes : "fait l'objet de"
    avis_smr }o--|| liens_avis_ct : "publié sur"
```

## Transformations appliquées

| Donnée brute | Valeur en base |
|---|---|
| Encodage Windows-1252 ou UTF-8 | UTF-8 |
| Dates `JJ/MM/AAAA`, `AAAAMMJJ`, `AAAA-MM-JJ` | ISO `AAAA-MM-JJ` |
| Prix `1,086,58` ou `2,18` | `1086.58`, `2.18` (REAL, euros) |
| Taux `65%`, `65 %` | `65` (INTEGER) |
| `oui` / `non`, `Oui` / `Non` | `1` / `0` |
| Voies `orale;sublinguale` | colonne d'origine + table `medicament_voies` |
| Espaces parasites, champs vides | supprimés, `NULL` |
"""


def data_dictionary() -> str:
    parts = [HEADER]
    for table in TABLES:
        parts.append(
            f"\n## `{table.name}`\n\n{table.description}  \nFichier source : `{table.source_file}`\n"
        )
        parts.append("| Colonne | Type | Description |\n|---|---|---|")
        for col in table.columns:
            flags = " 🔑" if col.primary_key else ""
            ref = f" → `{col.references}`" if col.references else ""
            parts.append(f"| `{col.name}`{flags} | {col.sql_type} | {col.description}{ref} |")
    return "\n".join(parts) + "\n"
