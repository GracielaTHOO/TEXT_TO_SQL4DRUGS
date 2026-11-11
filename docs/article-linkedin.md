# Brouillon d'article LinkedIn

*Brouillon à relire et à publier par l'autrice. Les chiffres viennent de [resultats.md](resultats.md).
Image suggérée : `assets/demo/demo.gif` (ou `assets/demo/question-2.png` si le GIF n'est pas accepté).*

---

**Un LLM de 7 milliards de paramètres, sans GPU, peut-il interroger la base publique des médicaments
en français ? Réponse mesurée : 7 fois sur 10.**

J'ai passé cinq semaines à construire un banc d'essai Text-to-SQL sur la Base de données publique des
médicaments (ANSM) : on pose une question en français, un LLM local écrit la requête SQL, la base
répond.

Ce que j'en retiens :

📏 **Mesurer petit, c'est mesurer du bruit.** Sur 60 questions, aucun écart entre modèles n'était
significatif, pas même entre 1,5 et 7 milliards de paramètres. Il en a fallu 110, avec intervalles de
confiance et tests appariés, pour départager les modèles.

🧠 **Le contexte métier bat les astuces de prompt.** Donner au modèle les libellés exacts de la base
(« Rupture de stock », « Commercialisée ») a rapporté 5 points sans rien casser. Choisir les exemples
par similarité en apporte 8 de plus, mais double la latence sur CPU.

🙅 **Savoir refuser, ça se mesure.** Le meilleur modèle refuse les 10 questions hors sujet (posologie,
ventes…) sans jamais refuser à tort.

🛡️ **La sécurité ne peut pas dépendre du modèle.** Face à des questions piégées, les modèles ont écrit
32 requêtes de suppression ou de modification. Toutes ont été bloquées par les garde-fous ; la base
n'a jamais bougé.

🏆 Recommandation pour un usage local : Qwen2.5-Coder 7B, 70,9 % de réponses justes, environ 12 s par
question sur un processeur ordinaire. Llama 3.1 8B : 59,1 %. Mistral 7B : 47,3 %.

Tout est ouvert : code, 120 questions, résultats de chaque run, tableau de bord et démo à lancer en
local avec Docker.
👉 https://github.com/GracielaTHOO/TEXT_TO_SQL4DRUGS

Prochaine étape : le même banc pour comparer Ollama et vLLM.

<!-- Phrase facultative, au choix de l'autrice : « Projet développé avec un assistant de code IA,
chaque chiffre vérifié par des tests et des runs enregistrés. » -->

#LLM #TextToSQL #OpenData #DataScience #IA #Santé
