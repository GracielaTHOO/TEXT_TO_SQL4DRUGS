"""Schéma relationnel de la BDPM : source unique de vérité.

Ce module décrit, pour chaque table SQLite :
- le fichier BDPM d'origine,
- les colonnes, leur type SQL et une description en français.

Les descriptions servent à la fois à générer la documentation (``docs/data.md``)
et à construire le prompt envoyé au LLM : le modèle voit exactement ce qui est documenté.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Column:
    name: str
    sql_type: str
    description: str
    primary_key: bool = False
    references: str | None = None  # "table(colonne)"


@dataclass(frozen=True)
class Table:
    name: str
    description: str
    source_file: str
    columns: tuple[Column, ...]
    indexes: tuple[tuple[str, ...], ...] = ()

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    def ddl(self) -> str:
        """Instruction ``CREATE TABLE`` commentée."""
        lines: list[str] = []
        pk = [c.name for c in self.columns if c.primary_key]
        for col in self.columns:
            line = f"  {col.name} {col.sql_type}"
            if col.references:
                line += f" REFERENCES {col.references}"
            lines.append(line)
        if pk:
            lines.append(f"  PRIMARY KEY ({', '.join(pk)})")
        body = ",\n".join(lines)
        return f"CREATE TABLE {self.name} (\n{body}\n);"

    def prompt_ddl(self) -> str:
        """DDL compacte annotée, optimisée pour le contexte du LLM."""
        lines = [f"-- {self.description}", f"CREATE TABLE {self.name} ("]
        for i, col in enumerate(self.columns):
            sep = "," if i < len(self.columns) - 1 else ""
            ref = f" REFERENCES {col.references}" if col.references else ""
            pk = " PRIMARY KEY" if col.primary_key and self._single_pk else ""
            lines.append(f"  {col.name} {col.sql_type}{pk}{ref}{sep} -- {col.description}")
        lines.append(");")
        return "\n".join(lines)

    @property
    def _single_pk(self) -> bool:
        return sum(c.primary_key for c in self.columns) == 1


CIS = "medicaments(cis)"

TABLES: tuple[Table, ...] = (
    Table(
        name="medicaments",
        description="Une ligne par spécialité pharmaceutique (code CIS).",
        source_file="CIS_bdpm.txt",
        columns=(
            Column("cis", "INTEGER", "Code CIS, identifiant de la spécialité", primary_key=True),
            Column("denomination", "TEXT", "Nom complet, ex. 'DOLIPRANE 1000 mg, comprimé'"),
            Column("forme_pharmaceutique", "TEXT", "ex. 'comprimé pelliculé', 'sirop'"),
            Column(
                "voies_administration", "TEXT", "Voies séparées par ';' (voir medicament_voies)"
            ),
            Column("statut_amm", "TEXT", "ex. 'Autorisation active', 'Autorisation abrogée'"),
            Column(
                "type_procedure_amm", "TEXT", "ex. 'Procédure nationale', 'Procédure centralisée'"
            ),
            Column("etat_commercialisation", "TEXT", "'Commercialisée' ou 'Non commercialisée'"),
            Column("date_amm", "DATE", "Date d'AMM au format ISO 'AAAA-MM-JJ'"),
            Column("statut_bdm", "TEXT", "'Alerte', 'Warning disponibilité' ou NULL"),
            Column("numero_autorisation_europeenne", "TEXT", "Numéro EU, NULL si national"),
            Column("titulaires", "TEXT", "Laboratoire(s) titulaire(s) de l'AMM, en majuscules"),
            Column(
                "surveillance_renforcee", "INTEGER", "1 si surveillance renforcée (triangle noir)"
            ),
        ),
        indexes=(("denomination",), ("titulaires",), ("etat_commercialisation",)),
    ),
    Table(
        name="medicament_voies",
        description="Voies d'administration éclatées : une ligne par (spécialité, voie).",
        source_file="CIS_bdpm.txt",
        columns=(
            Column("cis", "INTEGER", "Code CIS", primary_key=True, references=CIS),
            Column("voie", "TEXT", "ex. 'orale', 'cutanée', 'intraveineuse'", primary_key=True),
        ),
        indexes=(("voie",),),
    ),
    Table(
        name="presentations",
        description="Boîtes vendues (présentations), avec prix et remboursement.",
        source_file="CIS_CIP_bdpm.txt",
        columns=(
            Column("cip13", "TEXT", "Code CIP13 de la boîte", primary_key=True),
            Column("cip7", "TEXT", "Ancien code CIP7"),
            Column("cis", "INTEGER", "Code CIS", references=CIS),
            Column("libelle", "TEXT", "ex. 'plaquette(s) PVC aluminium de 8 comprimé(s)'"),
            Column("statut_administratif", "TEXT", "ex. 'Présentation active'"),
            Column("etat_commercialisation", "TEXT", "ex. 'Déclaration de commercialisation'"),
            Column("date_declaration", "DATE", "Date de déclaration de commercialisation (ISO)"),
            Column("agrement_collectivites", "INTEGER", "1 si agréé aux collectivités"),
            Column(
                "taux_remboursement", "INTEGER", "Taux en pourcentage (15, 30, 65, 100), NULL sinon"
            ),
            Column("prix_euros", "REAL", "Prix hors honoraires de dispensation, en euros"),
            Column("prix_ttc_euros", "REAL", "Prix honoraires de dispensation inclus, en euros"),
            Column("honoraires_euros", "REAL", "Honoraires de dispensation, en euros"),
            Column("indications_remboursement", "TEXT", "Texte des indications remboursables"),
        ),
        indexes=(("cis",), ("taux_remboursement",)),
    ),
    Table(
        name="compositions",
        description="Composition qualitative et quantitative : substances par spécialité.",
        source_file="CIS_COMPO_bdpm.txt",
        columns=(
            Column("cis", "INTEGER", "Code CIS", references=CIS),
            Column("element_pharmaceutique", "TEXT", "ex. 'comprimé', 'solution'"),
            Column("code_substance", "INTEGER", "Code de la substance"),
            Column("substance", "TEXT", "Nom de la substance en majuscules, ex. 'PARACÉTAMOL'"),
            Column("dosage", "TEXT", "ex. '1000 mg'"),
            Column("reference_dosage", "TEXT", "ex. 'un comprimé'"),
            Column(
                "nature_composant", "TEXT", "'SA' = substance active, 'FT' = fraction thérapeutique"
            ),
            Column("numero_liaison", "INTEGER", "Lien entre une SA et sa FT"),
        ),
        indexes=(("cis",), ("substance",), ("code_substance",)),
    ),
    Table(
        name="groupes_generiques",
        description="Groupes génériques : princeps et génériques substituables.",
        source_file="CIS_GENER_bdpm.txt",
        columns=(
            Column("id_groupe", "INTEGER", "Identifiant du groupe générique"),
            Column("libelle_groupe", "TEXT", "Libellé du groupe (substance, dosage, forme)"),
            Column("cis", "INTEGER", "Code CIS", references=CIS),
            Column(
                "type_generique",
                "INTEGER",
                "0=princeps, 1=générique, 2=complémentarité, 4=substituable",
            ),
            Column(
                "type_libelle",
                "TEXT",
                "'princeps', 'générique', 'génériques par complémentarité posologique' ou 'générique substituable'",
            ),
            Column("numero_tri", "INTEGER", "Ordre d'affichage dans le groupe"),
        ),
        indexes=(("id_groupe",), ("cis",)),
    ),
    Table(
        name="avis_smr",
        description="Avis de la HAS sur le Service Médical Rendu (SMR).",
        source_file="CIS_HAS_SMR_bdpm.txt",
        columns=(
            Column("cis", "INTEGER", "Code CIS", references=CIS),
            Column("code_dossier_has", "TEXT", "Code du dossier HAS"),
            Column(
                "motif_evaluation",
                "TEXT",
                "ex. 'Inscription (CT)', 'Renouvellement d''inscription (CT)'",
            ),
            Column("date_avis", "DATE", "Date de l'avis de la commission de la transparence (ISO)"),
            Column(
                "valeur_smr",
                "TEXT",
                "'Important', 'Modéré', 'Faible', 'Insuffisant', 'Non précisé'",
            ),
            Column("libelle_smr", "TEXT", "Texte de l'avis"),
        ),
        indexes=(("cis",), ("valeur_smr",)),
    ),
    Table(
        name="avis_asmr",
        description="Avis de la HAS sur l'Amélioration du Service Médical Rendu (ASMR).",
        source_file="CIS_HAS_ASMR_bdpm.txt",
        columns=(
            Column("cis", "INTEGER", "Code CIS", references=CIS),
            Column("code_dossier_has", "TEXT", "Code du dossier HAS"),
            Column("motif_evaluation", "TEXT", "Motif de l'évaluation"),
            Column("date_avis", "DATE", "Date de l'avis (ISO)"),
            Column("valeur_asmr", "TEXT", "'I' (majeure) à 'V' (absence), ou 'Commentaires'"),
            Column("libelle_asmr", "TEXT", "Texte de l'avis"),
        ),
        indexes=(("cis",), ("valeur_asmr",)),
    ),
    Table(
        name="conditions_prescription",
        description="Conditions de prescription et de délivrance.",
        source_file="CIS_CPD_bdpm.txt",
        columns=(
            Column("cis", "INTEGER", "Code CIS", references=CIS),
            Column("condition", "TEXT", "ex. 'liste I', 'liste II', 'prescription hospitalière'"),
        ),
        indexes=(("cis",),),
    ),
    Table(
        name="disponibilites",
        description="Ruptures et tensions d'approvisionnement déclarées.",
        source_file="CIS_CIP_Dispo_Spec.txt",
        columns=(
            Column("cis", "INTEGER", "Code CIS", references=CIS),
            Column("cip13", "TEXT", "Code CIP13, NULL si toutes les présentations"),
            Column(
                "code_statut",
                "INTEGER",
                "1=rupture, 2=tension, 3=arrêt de commercialisation, 4=remise à disposition",
            ),
            Column("statut", "TEXT", "Libellé du statut"),
            Column("date_debut", "DATE", "Date de début (ISO)"),
            Column("date_mise_a_jour", "DATE", "Date de mise à jour (ISO)"),
            Column(
                "date_remise_disposition", "DATE", "Date de remise à disposition (ISO), NULL sinon"
            ),
            Column("lien", "TEXT", "Lien vers le site de l'ANSM"),
        ),
        indexes=(("cis",), ("code_statut",)),
    ),
    Table(
        name="mitm",
        description="Médicaments d'intérêt thérapeutique majeur (MITM) avec code ATC.",
        source_file="CIS_MITM.txt",
        columns=(
            Column("cis", "INTEGER", "Code CIS", references=CIS),
            Column("code_atc", "TEXT", "Code ATC, ex. 'N02BE01' (paracétamol)"),
            Column("denomination", "TEXT", "Dénomination de la spécialité"),
            Column("lien", "TEXT", "Lien vers la fiche BDPM"),
        ),
        indexes=(("cis",), ("code_atc",)),
    ),
    Table(
        name="informations_importantes",
        description="Informations de sécurité importantes publiées par l'ANSM.",
        source_file="CIS_InfoImportantes.txt",
        columns=(
            Column("cis", "INTEGER", "Code CIS", references=CIS),
            Column("date_debut", "DATE", "Début de l'information (ISO)"),
            Column("date_fin", "DATE", "Fin de l'information (ISO)"),
            Column("texte", "TEXT", "Texte et lien de l'information"),
        ),
        indexes=(("cis",),),
    ),
    Table(
        name="liens_avis_ct",
        description="Liens vers les avis de la commission de la transparence de la HAS.",
        source_file="HAS_LiensPageCT_bdpm.txt",
        columns=(
            Column(
                "code_dossier_has",
                "TEXT",
                "Code du dossier HAS (cf. avis_smr, avis_asmr)",
                primary_key=True,
            ),
            Column("lien", "TEXT", "URL de l'avis sur le site de la HAS"),
        ),
    ),
)

TABLES_BY_NAME: dict[str, Table] = {t.name: t for t in TABLES}

SOURCE_FILES: tuple[str, ...] = tuple(dict.fromkeys(t.source_file for t in TABLES))


def schema_for_prompt(tables: list[str] | None = None) -> str:
    """Schéma annoté à inclure dans le prompt (toutes les tables par défaut)."""
    selected = [TABLES_BY_NAME[n] for n in tables] if tables else list(TABLES)
    return "\n\n".join(t.prompt_ddl() for t in selected)
