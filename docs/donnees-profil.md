# Profil des données

> Fichier généré par `medsql profile` sur la base réelle. Ne pas éditer à la main.

Généré le 2026-11-04 09:29 UTC, BDPM téléchargée le 2026-11-04T09:29:40+00:00.

## Volumétrie et complétude

| Table | Lignes | Colonnes avec valeurs manquantes (part de NULL) |
|---|---:|---|
| `medicaments` | 15 845 | `statut_bdm` 86 %, `numero_autorisation_europeenne` 85 % |
| `medicament_voies` | 19 560 | — |
| `presentations` | 20 918 | `taux_remboursement` 35 %, `prix_euros` 35 %, `prix_ttc_euros` 35 %, `honoraires_euros` 35 %, `indications_remboursement` 96 % |
| `compositions` | 32 297 | `dosage` 9 %, `reference_dosage` 9 % |
| `groupes_generiques` | 10 745 | — |
| `avis_smr` | 15 595 | — |
| `avis_asmr` | 10 146 | — |
| `conditions_prescription` | 28 513 | — |
| `disponibilites` | 725 | `cip13` 95 %, `date_remise_disposition` 84 % |
| `mitm` | 7 855 | — |
| `informations_importantes` | 0 | — |
| `liens_avis_ct` | 10 494 | — |

## Plages de dates

| Colonne | Min | Max |
|---|---|---|
| `medicaments.date_amm` | 1974-03-11 | 2026-07-28 |
| `presentations.date_declaration` | 1910-01-19 | 2924-11-29 |
| `avis_smr.date_avis` | 2002-12-18 | 2026-10-14 |
| `avis_asmr.date_avis` | 2002-12-18 | 2026-10-07 |
| `disponibilites.date_debut` | 2011-11-17 | 2027-07-01 |
| `disponibilites.date_mise_a_jour` | 2021-05-19 | 2026-11-02 |
| `disponibilites.date_remise_disposition` | 2025-10-06 | 2026-10-23 |
| `informations_importantes.date_debut` | — | — |
| `informations_importantes.date_fin` | — | — |

## Valeurs les plus fréquentes

### `medicaments.etat_commercialisation` (2 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| Commercialisée | 13 599 |
| Non commercialisée | 2 246 |

### `medicaments.statut_amm` (5 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| Autorisation active | 14 842 |
| Autorisation abrogée | 760 |
| Autorisation archivée | 229 |
| Autorisation retirée | 10 |
| Autorisation suspendue | 4 |

### `medicaments.type_procedure_amm` (8 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| Procédure nationale | 6 995 |
| Procédure décentralisée | 3 374 |
| Procédure centralisée | 2 386 |
| Procédure de reconnaissance mutuelle | 1 505 |
| Enreg homéo (Proc. Nat.) | 1 287 |
| Autorisation d'importation parallèle | 240 |
| Enreg phyto (Proc. Nat.) | 53 |
| Enreg phyto (Proc. Dec.) | 5 |

### `medicaments.statut_bdm` (2 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| NULL | 13 601 |
| Warning disponibilité | 2 227 |
| Alerte | 17 |

### `medicaments.forme_pharmaceutique` (368 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| comprimé pelliculé | 2 905 |
| solution injectable | 1 335 |
| comprimé | 1 288 |
| gélule | 1 097 |
| comprimé et solution(s) et granules et poudre et pommade | 1 059 |
| comprimé pelliculé sécable | 671 |
| comprimé sécable | 662 |
| solution à diluer pour perfusion | 273 |

### `medicament_voies.voie` (68 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| orale | 10 648 |
| intraveineuse | 2 109 |
| cutanée | 1 673 |
| sublinguale | 1 495 |
| sous-cutanée | 1 023 |
| intramusculaire | 603 |
| ophtalmique | 307 |
| inhalée | 300 |

### `presentations.taux_remboursement` (5 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| 65 | 10 872 |
| NULL | 7 257 |
| 100 | 1 267 |
| 30 | 1 150 |
| 15 | 368 |
| 35 | 4 |

### `presentations.statut_administratif` (2 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| Présentation active | 20 827 |
| Présentation abrogée | 91 |

### `compositions.nature_composant` (2 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| SA | 26 782 |
| FT | 5 515 |

### `groupes_generiques.type_libelle` (4 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| générique | 8 829 |
| princeps | 1 817 |
| générique substituable | 63 |
| génériques par complémentarité posologique | 36 |

### `avis_smr.valeur_smr` (9 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| Important | 9 658 |
| Insuffisant | 2 853 |
| Modéré | 1 685 |
| Faible | 1 171 |
| Commentaires | 99 |
| Non précisé | 88 |
| Important conditionnel | 18 |
| Faible conditionnel | 13 |

### `avis_asmr.valeur_asmr` (7 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| V | 7 793 |
| IV | 1 279 |
| III | 608 |
| II | 208 |
| Commentaires sans chiffrage de l'ASMR | 160 |
| I | 85 |
| V dans l'attente de données | 13 |

### `conditions_prescription.condition` (164 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| liste I | 10 942 |
| médicament nécessitant une surveillance particulière pendant le traitement | 1 746 |
| prescription hospitalière | 1 366 |
| liste II | 1 286 |
| prescription réservée aux spécialistes et services ONCOLOGIE MEDICALE | 801 |
| réservé à l'usage HOSPITALIER | 789 |
| prescription réservée aux médecins compétents en CANCEROLOGIE | 772 |
| prescription réservée aux spécialistes et services HEMATOLOGIE | 727 |

### `disponibilites.statut` (4 valeurs distinctes)

| Valeur | Lignes |
|---|---:|
| Tension d'approvisionnement | 521 |
| Remise à disposition | 117 |
| Rupture de stock | 62 |
| Arrêt de commercialisation | 25 |
