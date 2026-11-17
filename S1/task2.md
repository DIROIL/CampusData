# Tâche 2 - Backlog

Priorité : P1 = indispensable pour la démo, P2 = important, P3 = si le temps le permet.

## User stories

| ID | L'utilisateur peut… | Prio | Resp. |
|---|---|---|---|
| US01 | créer un jeu de données | P1 | Diroil |
| US02 | lister et ouvrir les jeux | P1 | Diroil |
| US03 | supprimer un jeu | P2 | Diroil |
| US04 | déposer un fichier CSV | P1 | Diroil |
| US05 | voir son dépôt traité | P1 | Diroil |
| US06 | voir les lignes rejetées | P2 | Diroil |
| US07 | redéposer un fichier sans doublon | P1 | Diroil |
| US08 | consulter les indicateurs | P1 | Diroil |
| US09 | relancer un dépôt échoué | P2 | Diroil |
| US10 | compter sur un service fiable | P1 | Diroil |

## Scénarios (Étant donné / Quand / Alors)

| ID | Type | Étant donné | Quand | Alors |
|---|---|---|---|---|
| US01 | Positif | aucun jeu nommé « Salles A » | je crée « Salles A » avec un responsable | l'API répond 201 et le jeu apparaît dans la liste avec 0 mesure |
| US01 | Erreur | un jeu « Salles A » existant | je crée à nouveau « Salles A » | l'API répond 409 et la liste compte toujours un seul « Salles A » |
| US02 | Positif | un jeu contenant 63 mesures | j'affiche la liste puis j'ouvre le jeu | il apparaît avec 63 mesures et l'ouverture répond 200 |
| US02 | Erreur | un identifiant qui n'existe pas | j'ouvre ce jeu | l'API répond 404 |
| US03 | Positif | un jeu avec 63 mesures | je confirme la suppression | l'API répond 204 sans corps, puis l'ouvrir répond 404 et aucune de ses mesures ne reste en base |
| US03 | Erreur | la fenêtre de confirmation ouverte | je clique « Annuler » | aucune requête n'est envoyée et le jeu reste dans la liste |
| US04 | Positif | un jeu existant | je dépose mesures-salles-2026-10-05.csv | l'API répond 202 et le dépôt est enregistré en pending |
| US04 | Erreur | un jeu existant | je dépose un fichier vide | l'API refuse le dépôt (422) et aucun dépôt n'est créé |
| US05 | Positif | un dépôt pending du fichier de référence | le worker le traite | il passe à succeeded avec 63 acceptées |
| US05 | Erreur | un dépôt de en-tete-invalide.csv | le worker le traite | il passe à failed avec la raison « en-tête invalide » et 0 mesure insérée |
| US06 | Positif | un dépôt de mesures-avec-erreurs.csv | le worker le traite | il est succeeded avec 4 acceptées, 7 rejetées et 1 doublon ; chaque rejet indique son numéro de ligne et sa raison (ex. ligne 5 : CO2 négatif) |
| US06 | Erreur | une ligne avec temperature_c = abc | elle est traitée | elle est rejetée et comptée, et le dépôt continue avec les lignes suivantes (il ne passe pas à failed) |
| US07 | Positif | un jeu qui contient déjà les 63 mesures du fichier de référence | je dépose à nouveau ce fichier et le worker le traite | le dépôt est succeeded avec 0 acceptée et 63 doublons, et le jeu compte toujours 63 mesures |
| US07 | Erreur | un fichier contenant deux fois la même salle à la même heure | il est traité | la seconde ligne est comptée en doublon et non insérée |
| US08 | Positif | les 63 mesures de référence | je demande les indicateurs | j'obtiens 3 salles (A101, A102, B201) avec 21 mesures chacune, et le CO2 moyen/min/max, la température et l'humidité moyennes |
| US08 | Erreur | une période où from est après to | je demande les indicateurs | l'API répond 422 et l'interface affiche un message lisible |
| US09 | Positif | un dépôt failed | je clique « Relancer » | il repasse en pending, puis le worker le traite à nouveau |
| US09 | Erreur | un dépôt succeeded | je demande sa relance | l'API répond 409 et son statut reste succeeded |
| US10 | Positif | un jeu de 63 mesures | je redémarre les conteneurs sans supprimer le volume | le jeu est toujours là avec 63 mesures |
| US10 | Erreur | une base PostgreSQL arrêtée | j'appelle /health/ready | l'API répond 503, tandis que /health/live répond toujours 200 |

## Cas d'erreur obligatoires (+ 2 bonus)

| Cas | US | Résultat attendu |
|---|---|---|
| Nom de jeu déjà utilisé | US01 | 409, aucun jeu créé |
| Fichier vide | US04 | 422, aucun dépôt créé |
| En-tête invalide | US05 | dépôt failed, 0 mesure insérée |
| Relance d'un dépôt qui n'est pas failed | US09 | 409, statut inchangé |
| Bonus : fichier de plus de 1 Mio | US04 | 413 |
| Bonus : fichier qui n'est pas du CSV | US04 | 415 |

À vérifier dans le contrat HTTP (tâche 5) : code exact pour un fichier vide (422 supposé) et réponse d'une relance acceptée (retour en pending supposé).
