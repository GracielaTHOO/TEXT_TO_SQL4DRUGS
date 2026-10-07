# Feuille de route

Le projet avance par incréments publiés les lundis, mercredis et vendredis.

## v0.1 — socle (fait)
- [x] Base SQLite normalisée et documentée
- [x] Garde-fous SQL
- [x] Clients Ollama et compatible OpenAI
- [x] 60 questions, métrique d'exactitude, tableau de bord
- [x] Démo Gradio, image Hugging Face Spaces, CI

## v0.2 — premiers chiffres
- [ ] Runs complets sur Qwen2.5-Coder 1.5B, 3B et 7B (workflow GitHub Actions)
- [ ] Ablations : zero-shot contre few-shot, avec et sans auto-correction
- [ ] Analyse d'erreurs : typologie des échecs (jointure manquante, mauvais filtre, texte mal orthographié…)
- [ ] Space en ligne

## v0.3 — robustesse
- [ ] Jeu porté à 120 questions, dont des paraphrases d'une même intention
- [ ] Intervalles de confiance (bootstrap) dans le tableau de bord
- [ ] Questions hors périmètre : le modèle doit savoir répondre « je ne sais pas »
- [ ] Comparaison avec d'autres familles (Llama, Mistral, Gemma, SQLCoder)

## v0.4 — qualité de réponse
- [ ] Reformulation du résultat en phrase française
- [ ] Sélection dynamique des exemples few-shot par similarité
- [ ] Mesure du coût par question (énergie, temps GPU), en lien avec le banc Ollama contre vLLM
