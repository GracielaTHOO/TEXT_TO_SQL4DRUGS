# Profil des données

> Fichier généré par `medsql profile` sur la base réelle. Ne pas éditer à la main.

Généré le 2026-10-28 13:42 UTC, BDPM téléchargée le 2026-10-28T13:42:23+00:00.

## Volumétrie et complétude

| Table | Lignes | Colonnes avec valeurs manquantes (part de NULL) |
|---|---:|---|
| `medicaments` | 15 883 | `statut_bdm` 86 %, `numero_autorisation_europeenne` 85 % |
| `medicament_voies` | 19 648 | — |
| `presentations` | 20 882 | `taux_remboursement` 35 %, `prix_euros` 35 %, `prix_ttc_euros` 35 %, `honoraires_euros` 35 %, `indications_remboursement` 96 % |
| `compositions` | 32 439 | `dosage` 9 %, `reference_dosage` 9 % |
| `groupes_generiques` | 10 737 | — |
| `avis_smr` | 15 547 | — |
| `avis_asmr` | 10 117 | — |
| `conditions_prescription` | 28 532 | — |
| `disponibilites` | 706 | `cip13` 95 %, `date_remise_disposition` 84 % |
| `mitm` | 7 855 | — |
| `informations_importantes` | 0 | — |
| `liens_avis_ct` | 10 465 | — |

## Plages de dates

| Colonne | Min | Max |
|---|---|---|
| `medicaments.date_amm` | 1974-03-11 | 2026-07-28 |
| `presentations.date_declaration` | 1910-01-19 | 2924-11-29 |
| `avis_smr.date_avis` | 2002-12-18 | 2026-09-16 |
| `avis_asmr.date_avis` | 2002-12-18 | 2026-09-16 |
| `disponibilites.date_debut` | 2011-11-17 | 2027-07-01 |
| `disponibilites.date_mise_a_jour` | 2021-05-19 | 2026-10-27 |
| `disponibilites.date_remise_disposition` | 2025-10-06 | 2026-10-23 |
| `informations_importantes.date_debut` | — | — |
| `informations_importantes.date_fin` | — | — |

## Valeurs les plus fréquentes

### `medicaments.etat_commercialisation` (2 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| Commercialisée | 13 650 |
| Non commercialisée | 2 233 |

### `medicaments.statut_amm` (5 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| Autorisation active | 14 940 |
| Autorisation abrogée | 724 |
| Autorisation archivée | 205 |
| Autorisation retirée | 10 |
| Autorisation suspendue | 4 |

### `medicaments.type_procedure_amm` (8 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| Procédure nationale | 7 013 |
| Procédure décentralisée | 3 377 |
| Procédure centralisée | 2 373 |
| Procédure de reconnaissance mutuelle | 1 505 |
| Enreg homéo (Proc. Nat.) | 1 316 |
| Autorisation d'importation parallèle | 239 |
| Enreg phyto (Proc. Nat.) | 55 |
| Enreg phyto (Proc. Dec.) | 5 |

### `medicaments.statut_bdm` (2 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| NULL | 13 652 |
| Warning disponibilité | 2 214 |
| Alerte | 17 |

### `medicaments.forme_pharmaceutique` (369 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| comprimé pelliculé | 2 910 |
| solution injectable | 1 329 |
| comprimé | 1 284 |
| gélule | 1 097 |
| comprimé et solution(s) et granules et poudre et pommade | 1 059 |
| comprimé pelliculé sécable | 673 |
| comprimé sécable | 663 |
| solution à diluer pour perfusion | 273 |

### `medicament_voies.voie` (68 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| orale | 10 689 |
| intraveineuse | 2 114 |
| cutanée | 1 691 |
| sublinguale | 1 524 |
| sous-cutanée | 1 016 |
| intramusculaire | 601 |
| ophtalmique | 308 |
| inhalée | 300 |

### `presentations.taux_remboursement` (5 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| 65 | 10 850 |
| NULL | 7 262 |
| 100 | 1 252 |
| 30 | 1 145 |
| 15 | 369 |
| 35 | 4 |

### `presentations.statut_administratif` (2 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| Présentation active | 20 791 |
| Présentation abrogée | 91 |

### `compositions.nature_composant` (2 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| SA | 26 915 |
| FT | 5 524 |

### `groupes_generiques.type_libelle` (4 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| générique | 8 832 |
| princeps | 1 808 |
| générique substituable | 61 |
| génériques par complémentarité posologique | 36 |

### `avis_smr.valeur_smr` (9 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| Important | 9 634 |
| Insuffisant | 2 838 |
| Modéré | 1 677 |
| Faible | 1 170 |
| Commentaires | 99 |
| Non précisé | 88 |
| Important conditionnel | 18 |
| Faible conditionnel | 13 |

### `avis_asmr.valeur_asmr` (7 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| V | 7 767 |
| IV | 1 277 |
| III | 607 |
| II | 208 |
| Commentaires sans chiffrage de l'ASMR | 160 |
| I | 85 |
| V dans l'attente de données | 13 |

### `conditions_prescription.condition` (164 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| liste I | 10 943 |
| médicament nécessitant une surveillance particulière pendant le traitement | 1 747 |
| prescription hospitalière | 1 368 |
| liste II | 1 288 |
| prescription réservée aux spécialistes et services ONCOLOGIE MEDICALE | 800 |
| réservé à l'usage HOSPITALIER | 793 |
| prescription réservée aux médecins compétents en CANCEROLOGIE | 771 |
| prescription réservée aux spécialistes et services HEMATOLOGIE | 727 |

### `disponibilites.statut` (4 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| Tension d'approvisionnement | 503 |
| Remise à disposition | 116 |
| Rupture de stock | 63 |
| Arrêt de commercialisation | 24 |
