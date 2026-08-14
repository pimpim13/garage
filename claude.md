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
- Une offre **famille** — mécanisme de décompte encore à préciser (voir « Points à confirmer avec le client »)
- Des offres **personnalisées** (en prévoir 2 au début)

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

## Gestion des séances achetées

- Gestion de l'achat de séances et du nombre de séances restantes disponibles (pour l'instant géré par l'admin ou le gestionnaire)
- Tant que le paiement en ligne n'est pas implémenté, c'est le gestionnaire ou l'admin qui met à jour :
  - les informations de paiement
  - le nombre de séances achetées
- Les dates d'achat de séances sont suivies par membre

## Jokers

- Chaque membre peut obtenir un ou plusieurs jokers de la part du gestionnaire (ou admin)
- L'obtention d'un joker supplémentaire est à la discrétion du gestionnaire

## Inscription / désinscription

- Les membres peuvent s'inscrire et se désinscrire d'une séance
- Chaque action est horodatée
- Le nombre de séances disponibles est décrémenté à l'inscription
- L'admin ou le gestionnaire fixe, individuellement par membre, une tolérance de nombre de séances négatif (par défaut à **0**)

### Règle de désinscription tardive

- Si un membre se désinscrit à une échéance trop proche (définie par le créateur de la séance) :
  - un **joker** lui est décompté
  - le nombre de séances est recrédité
- Si aucun joker n'est disponible, la séance est alors décomptée du nombre de séances restantes

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

## Points à confirmer avec le client

- **Offre famille** : les séances sont-elles décomptées d'un **pool partagé** (un seul carnet pour le foyer) ou de **carnets individuels liés** (un solde par membre, tarif réduit groupé) ?
- **Liste d'attente** : quand une séance est complète, faut-il une file d'attente avec promotion automatique en cas de désistement, ou simplement fermer l'inscription (sans liste d'attente au démarrage) ?
- **Péremption des carnets** : les séances achetées ont-elles une date limite d'utilisation, ou restent-elles valables sans limite de temps ?

## Design

Structure et parcours UX (vue calendrier hebdomadaire, navigation par pastilles de jour, cards) inspirés de l'application **peppy.cool**.

L'habillage graphique (logo, couleurs) suit en revanche l'identité réelle du Garage, de style street-workout/graffiti :
- Noir : `#201e1f`
- Vert accent : `#80b048`
