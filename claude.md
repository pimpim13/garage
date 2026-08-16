# Création d'une web App de gestion de salle de sport — le Garage

Nom de la salle : **le Garage** (coaching : Loïc Fitness Coaching).

## Stack technique

- Langage : **Python**, framework **Django 5.2**, **Bootstrap 5** (via django-crispy-forms)
- Application **responsive**, utilisable sur smartphone
- Dépôt GitHub : `pimpim13/garage`

## Profils utilisateurs

- **Administrateur** (super utilisateur)
- **Gestionnaire**
- **Membre**

Le **coach** n'est pas un rôle séparé : c'est un Gestionnaire (ou l'Admin) désigné comme animateur d'une séance donnée.

## Paiement

L'application doit être prête à intégrer un système de paiement, qui ne sera pas implémenté dans un premier temps.

## Offres

Le catalogue des offres doit être **évolutif**. Offres prévues au démarrage :

- Une première offre à **100 €** le carnet de **11 séances**
- Une offre **famille**, fonctionnant en **pool de séances partagé** (voir « Familles » ci-dessous)
- Des offres **personnalisées** (en prévoir 2 au début)

## Familles

Un membre peut être rattaché à une **famille**, qui regroupe plusieurs membres liés (ex. un foyer) :

- Le crédit de séances de l'offre famille est **partagé** entre tous les membres de la famille : une séance est décomptée du même pool, quel que soit le membre lié qui s'inscrit.
- La **tolérance de séances négatives** est définie au niveau de la famille (pas individuellement par membre) et s'applique de la même façon à tous les membres liés, pour éviter toute ambiguïté entre membres d'une même famille.

## Calendrier des séances

- Exposition d'un calendrier des séances
- Nombre maximum de participants fixé par le créateur de la séance (gestionnaire/coach ou admin)
- Des **modèles de séance type** disponibles

### Vue calendrier

- Représentation graphique de l'occupation des séances, en vue **calendrier hebdomadaire**
- Navigation en avant / en arrière
- Accès à une **vue journalière** et une **vue par séance**
- Depuis cette vue, le membre peut s'inscrire ou se désinscrire
- Affichage de la liste des participants déjà inscrits ainsi que du coach de la séance

### Annulation d'une séance par le gestionnaire

- Si une séance n'a pas atteint un minimum de **4 participants** inscrits, le gestionnaire (ou l'admin) peut l'annuler
- Les membres inscrits sont notifiés (email)
- Leur crédit de séance est restauré (recrédité), sans impact sur leurs jokers

## Gestion des séances achetées

- Gestion de l'achat de séances et du nombre de séances restantes disponibles (pour l'instant géré par l'admin ou le gestionnaire)
- Tant que le paiement en ligne n'est pas implémenté, c'est le gestionnaire ou l'admin qui met à jour :
  - les informations de paiement
  - le nombre de séances achetées
- Les dates d'achat de séances sont suivies par membre
- Les séances achetées ont une **date de péremption** : **6 mois** après l'achat par défaut, prolongeable à la discrétion du gestionnaire (ex. en cas de blessure)
- Sur la fiche d'une séance, le gestionnaire/admin voit, pour chaque participant inscrit, son nombre de séances restantes, avec la possibilité de l'ajuster (**+11** pour un carnet, **+1**, **−1**)
- Un indicateur visuel signale l'état du solde de chaque membre par rapport à sa tolérance négative (sa propre tolérance, ou celle de sa famille le cas échéant), à la fois sur la fiche séance et sur la liste des membres :
  - **Vert** : solde positif
  - **Orange** : solde à zéro, ou négatif sans avoir atteint la tolérance
  - **Rouge** : tolérance négative atteinte

## Jokers

- Chaque membre peut obtenir un ou plusieurs jokers de la part du gestionnaire (ou admin)
- L'obtention d'un joker supplémentaire est à la discrétion du gestionnaire

## Inscription / désinscription

- Les membres peuvent s'inscrire et se désinscrire d'une séance
- Chaque action est horodatée
- Le nombre de séances disponibles est décrémenté à l'inscription
- L'admin ou le gestionnaire fixe une tolérance de nombre de séances négatif (par défaut à **0**), individuellement par membre, ou au niveau de la famille si le membre y est rattaché

### Règle de désinscription tardive

- Si un membre se désinscrit à une échéance trop proche (définie par le créateur de la séance) :
  - un **joker** lui est décompté
  - le nombre de séances est recrédité
- Si aucun joker n'est disponible, la séance est alors décomptée du nombre de séances restantes

### Liste d'attente

- Quand une séance est complète, un membre peut se positionner en **liste d'attente**
- En cas de désistement, le membre le plus haut dans la file est **automatiquement inscrit**
- Il est alerté par notification (email pour l'instant)
- Une fois inscrit automatiquement, il devient un membre inscrit à part entière : les règles communes s'appliquent, y compris la règle de désinscription tardive — s'il ne peut plus assister, il doit se désinscrire dans les délais, sous peine d'entamer son crédit joker

## Gestion des membres

- Le gestionnaire ou l'admin peut créer un compte membre (nom, prénom, téléphone, tolérance, mot de passe initial)
- Le gestionnaire ou l'admin peut **désactiver** un membre plutôt que le supprimer : la connexion est bloquée mais son historique (inscriptions, achats, mouvements) est conservé ; la désactivation est réversible

## Droits d'accès

- Un membre seul peut s'inscrire ou se désinscrire lui-même
- L'administrateur ou le gestionnaire ont tous les droits

## Notifications

Système de notification (par email dans un premier temps, extensible ensuite à SMS, WhatsApp, etc.), avec choix des notifications par le membre :

- Inscription à une séance
- Désinscription
- Joker utilisé
- Ouverture d'une nouvelle date de séance
- Nombre de séances restantes faible
- …

## Design

Structure et parcours UX (vue calendrier hebdomadaire, navigation par pastilles de jour, cards) inspirés de l'application **peppy.cool**.

L'habillage graphique (logo, couleurs) suit en revanche l'identité réelle du Garage, de style street-workout/graffiti :
- Noir : `#201e1f`
- Vert accent : `#80b048`
