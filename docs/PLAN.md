# Plan de développement

**Objectif final (v1.0.0, vendredi 13 novembre 2026)** : un banc Text-to-SQL reproductible sur la BDPM qui
compare au moins 6 LLM locaux sur 120 questions, avec intervalles de confiance et analyse d'erreurs, une démo
publique sur Hugging Face Spaces, un tableau de bord public sur GitHub Pages et une note de synthèse prête à
publier.

Le travail avance en **séances le lundi, le mercredi et le vendredi**. Chaque séance livre un incrément
fonctionnel : code, tests verts (ruff, mypy strict, pytest), documentation et CHANGELOG à jour, poussé sur
`main`. Les cases sont cochées au fil de l'eau ; ce fichier fait foi pour la routine automatique.

Légende : 🙋 = action de Graciela nécessaire.

## Jalon 1 : premiers chiffres réels (v0.2, 7 → 16 octobre)

- [x] **S0 · mer. 7 oct.** Socle v0.1 : base SQLite, garde-fous, clients LLM, 60 questions, CLI, démo, tableau de bord, CI.
- [x] **S1 · ven. 9 oct.** Premier run réel (workflow d'évaluation, 10 questions, Qwen2.5-Coder 1.5B).
      Corriger le chargement et les questions dont la référence renvoie 0 ligne sur la vraie BDPM.
      Publier les chiffres de la base (`results/bdpm_stats.json`) et un profil des données (`docs/donnees-profil.md`).
- [x] **S2 · lun. 12 oct.** Runs complets Qwen2.5-Coder 1.5B, 3B et 7B. Premier tableau de résultats dans le README.
      🙋 Activer GitHub Pages (*Settings → Pages → Source : GitHub Actions*)  : fait le 13 octobre (dépôt public).
- [x] **S3 · mer. 14 oct.** Ablations : zero-shot contre few-shot, avec et sans auto-correction
      (entrées du workflow, colonne « configuration » du tableau de bord).
      Ablation supplémentaire : libellés exacts des colonnes catégorielles dans le schéma du prompt
      (constat de S2 sur `disponibilites.statut`).
- [ ] **S4 · ven. 16 oct.** Libellés exacts retenus dans la configuration par défaut (constat de S3).
      Analyse d'erreurs automatique (`medsql.eval.errors`) : table manquante, mauvaise
      jointure, filtre texte, agrégat, lignes en trop ou en moins. Section dédiée du tableau de bord.
      Release **v0.2.0**.

## Jalon 2 : démo publique et rigueur statistique (v0.3, 19 → 30 octobre)

- [ ] **S5 · lun. 19 oct.** Démo en ligne sur Hugging Face Spaces.
      🙋 Créer un jeton d'écriture Hugging Face et l'ajouter en secret `HF_TOKEN` du dépôt.
- [ ] **S6 · mer. 21 oct.** Intervalles de confiance par bootstrap et test de McNemar entre deux modèles ;
      barres d'erreur dans le tableau de bord.
- [ ] **S7 · ven. 23 oct.** Jeu porté à 90 questions : paraphrases d'une même intention pour mesurer la robustesse
      à la formulation.
- [ ] **S8 · lun. 26 oct.** Jeu porté à 120 questions, dont 10 hors périmètre : le modèle doit s'abstenir
      (métrique d'abstention correcte).
- [ ] **S9 · mer. 28 oct.** Comparaison multi-familles : Llama 3.1 8B, Mistral 7B, Gemma 2 9B, SQLCoder, Qwen2.5-Coder.
- [ ] **S10 · ven. 30 oct.** Sélection dynamique des exemples few-shot par similarité (embeddings locaux),
      mesurée contre les exemples fixes. Release **v0.3.0**.

## Jalon 3 : produit fini (v1.0, 2 → 13 novembre)

- [ ] **S11 · lun. 2 nov.** Démo : réponse rédigée en français sous le tableau, export CSV, historique des questions.
- [ ] **S12 · mer. 4 nov.** Performance : cache des réponses, mesure du temps de premier token et des tokens/s,
      coût CPU par question (passerelle vers le projet « Ollama contre vLLM »).
- [ ] **S13 · ven. 6 nov.** Sécurité : jeu de tests adverses (injection dans la question, SQL piégé, requêtes
      coûteuses), rapport dans `docs/securite.md`.
- [ ] **S14 · lun. 9 nov.** Finitions : captures et GIF de la démo, badge de couverture, relecture complète
      de la documentation.
- [ ] **S15 · mer. 11 nov.** Note de synthèse des résultats (`docs/resultats.md`) et brouillon d'article LinkedIn.
- [ ] **S16 · ven. 13 nov.** Release **v1.0.0** : tag, notes de version, résultats figés, démo et tableau de bord à jour.

## Règles de conduite

- Une séance ne commence pas de nouvelle tâche tant que la CI de la précédente n'est pas verte.
- Un chiffre publié vient toujours d'un run enregistré dans `results/runs/` (jamais saisi à la main).
- Si une séance prend du retard, la suivante la termine d'abord ; le plan est décalé, jamais compressé au
  détriment des tests.
- Les commits suivent Conventional Commits, en français, et ne sont jamais antidatés.
