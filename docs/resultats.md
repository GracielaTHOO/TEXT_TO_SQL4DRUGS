# Synthèse des résultats

*Note arrêtée le 11 novembre 2026, avant la v1.0.0. Chaque chiffre vient d'un run enregistré dans
`results/runs/` ou `results/security/` ; la méthode est détaillée dans [evaluation.md](evaluation.md)
et [securite.md](securite.md).*

## La question

Un petit LLM qui tourne sur un ordinateur portable, sans GPU ni service externe, peut-il répondre en
français à des questions sur la Base de données publique des médicaments en écrivant lui-même le SQL ?
Et peut-on mesurer honnêtement à quel point ?

## Le dispositif

- **Données** : les 11 fichiers de la BDPM (ANSM), normalisés en 12 tables SQLite, reconstruits à
  chaque mise à jour mensuelle.
- **Jeu de test** : 120 questions écrites à la main, 110 dans le périmètre de la base (dont
  30 reformulations) et 10 hors périmètre, auxquelles la seule bonne réponse est de refuser.
- **Mesure** : une réponse est juste si son SQL, exécuté, renvoie les mêmes lignes que la requête de
  référence. Intervalles de confiance par bootstrap, comparaisons appariées par test de McNemar.
- **Matériel** : runner GitHub standard, 4 vCPU, sans GPU, Ollama. Cinq familles de modèles (Qwen, Llama, Mistral, SQLCoder, Gemma),
  de 1,5 à 9 milliards de paramètres.

## Les chiffres à retenir

| Configuration | Exactitude (110 questions) | IC 95 % | Refus corrects (10) | Latence médiane |
|---|---:|---:|---:|---:|
| Qwen2.5-Coder 7B, exemples choisis par similarité | **79,1 %** | 70,9 – 86,4 % | 8 | 27,2 s |
| Qwen2.5-Coder 7B, configuration par défaut | 70,9 % | 62,7 – 79,1 % | **10** | 12,4 s |
| Qwen2.5-Coder 3B | 61,8 % | 52,7 – 70,9 % | 4 | 8,0 s |
| Llama 3.1 8B | 59,1 % | 50,0 – 68,2 % | 9 | 15,7 s |
| Qwen2.5-Coder 1.5B | 50,9 % | 41,8 – 60,0 % | 7 (et 8 refus à tort) | 2,6 s |
| Mistral 7B | 47,3 % | 38,2 – 56,4 % | 1 | 11,5 s |
| SQLCoder 7B | 1,8 % | 0,0 – 4,5 % | 4 | 127,1 s |

Runs du 4 novembre 2026 pour Qwen, du 28 octobre pour les autres familles. Gemma 2 9B n'a répondu à
aucune question en moins de 180 s sur ce matériel.

## Ce que l'on a appris

**1. La taille compte, la spécialisation aussi.** Le 7B dépasse le 1.5B de 20 points (31 questions
gagnées, 9 perdues, p < 0,001). À taille égale, le Qwen spécialisé en code dépasse Llama 3.1 8B de
13 points (p = 0,02) et Mistral 7B de 24 points. Un modèle spécialisé SQL mais entraîné à la
complétion (SQLCoder) échoue presque totalement en mode conversation : le format compte autant que
la spécialité.

**2. Mesurer petit, c'est mesurer du bruit.** Sur les 60 questions de départ, aucun écart n'était
significatif, pas même 7B contre 1.5B (p = 0,26). Il a fallu passer à 110 questions pour que cet écart
devienne net. Le même 7B, rejoué cinq fois sur le même jeu entre le 26 octobre et le 4 novembre,
oscille entre 70,9 et 72,7 % (la BDPM du mois a changé entre-temps) : deux questions d'écart, l'ordre
de grandeur d'un « gain » que l'on aurait été tenté d'annoncer.

**3. Le contexte métier rapporte plus que les astuces de prompt.** Lister dans le prompt les libellés
exacts des colonnes catégorielles (« Rupture de stock », « Commercialisée ») a rapporté 5 points au 7B
sur les 60 questions de l'époque, sans en perdre une seule. Les exemples choisis par similarité dans une réserve de 32 apportent
de 7 à 9 points selon la taille, surtout sur les questions difficiles (7B : 3 sur 16 justes avec les
exemples fixes, 8 sur 16 avec les exemples choisis). Le gain s'est répété dans le même sens lors des
deux mesures, mais celui du 7B reste juste au-dessus du seuil de 5 % (p = 0,06).

**4. Savoir refuser se mesure aussi.** Le 7B refuse les 10 questions hors périmètre sans jamais
refuser à tort. Le 1.5B en refuse 7, mais refuse aussi 8 questions auxquelles la base répond. Avec les
exemples choisis par similarité, le 7B ne refuse plus que 8 questions sur 10 : le gain d'exactitude a
un prix.

**5. La vitesse dépend surtout de ce que le serveur peut réutiliser.** Avec un prompt identique d'une
question à l'autre, Ollama réutilise les 3 000 tokens déjà lus : le 7B commence à répondre en 3 s.
Quand les exemples changent à chaque question, il doit relire et le premier token arrive après 18,7 s.
Sur ce matériel, le meilleur score coûte donc un doublement de la latence et du temps CPU.

**6. La sécurité ne peut pas dépendre du modèle.** Face à 28 questions piégées, les modèles ont écrit
32 requêtes d'écriture ou d'administration ; le 3B a obéi à 8 injections directes sur 10. Toutes ont
été bloquées par les garde-fous, la base n'a jamais changé. Sonder ces garde-fous a aussi révélé trois
failles corrigées depuis : allocation de centaines de mégaoctets, fuite d'une adresse mémoire, questions
de longueur illimitée.

## Ce qui reste difficile

- **Les questions difficiles** (plusieurs jointures, sous-requêtes) : 19 % de réussite pour le 7B par
  défaut, 50 % avec les exemples choisis. Les jointures restent la première cause d'erreur.
- **La robustesse à la formulation** est bonne pour le 7B (93 % des paires reformulées ont le même
  sort), plus fragile pour le 1.5B (70 %).
- **Le jeu de test** a été écrit par l'auteur du projet ; 110 questions laissent un intervalle de
  confiance d'environ ±8 points.

## Recommandation

Pour un usage local sur CPU : **Qwen2.5-Coder 7B avec la configuration par défaut**. Il répond juste
à 7 questions sur 10, refuse correctement ce qui sort de la base et donne une réponse en une douzaine
de secondes. Les exemples choisis par similarité valent la peine dès qu'un GPU ou un serveur qui
réutilise mieux le préfixe du prompt (vLLM) rend leur coût négligeable : c'est la question du prochain
projet, « Ollama contre vLLM », qui reprendra ce banc et ses métriques.
