# Tâche 1 - Reformuler le besoin

| # | Question | Réponse |
|---|---|---|
| 1 | Qui utilise l'application ? | L'application est utilisée par une personne chargée de suivre la qualité de l'air des salles du campus, par exemple un agent des services techniques. Elle se déclare responsable d'un jeu de données, sans compte ni mot de passe. |
| 2 | Quel problème a-t-elle aujourd'hui ? | Les capteurs produisent des fichiers de mesures (CO₂, température, humidité) qu'il faut ouvrir et comparer à la main. Ça prend du temps, les erreurs passent inaperçues et un même fichier peut être compté deux fois. |
| 3 | Quelle est son action principale ? | Elle crée un jeu de données, y dépose un fichier CSV de mesures, puis consulte le rapport du dépôt et les indicateurs par salle : CO₂ moyen, minimum et maximum, température et humidité moyennes. |
| 4 | Quelles données doivent être conservées ? | Les jeux de données, l'historique des dépôts avec leur statut et leurs compteurs (acceptées, rejetées, doublons), et les mesures elles-mêmes, sans aucun doublon. |
| 5 | Qu'est-ce qui est exclu ? | zero authentification, pas de connexion directe aux capteurs en temps réel, pas d'alertes automatiques, pas de modification d'une mesure à la main. |
