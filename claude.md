# Création d'une web App de gestion de salle de sport — le Garage

Nom de la salle : **le Garage** (coaching : Loïc Fitness Coaching).

## Stack technique

- Langage : **Python**, framework **Django 5.2**, **Bootstrap 5** (via django-crispy-forms)
- Application **responsive**, utilisable sur smartphone
- Dépôt GitHub : `pimpim13/garage`
- Configuration sensible (clé secrète Django, hosts autorisés, identifiants ntfy.sh) isolée dans un fichier `.env` local (non versionné, voir `.env.example` pour la liste des variables attendues)

## Profils utilisateurs

- **Administrateur** (super utilisateur)
- **Coach gestionnaire** — a tous les droits de gestion actuels (ex-« Gestionnaire »)
- **Coach** — a les mêmes droits qu'un Membre, à l'exception de la possibilité de marquer un membre inscrit comme non présent à une séance
- **Membre**

Un « coach » au sens animateur d'une séance peut être soit un Coach gestionnaire, soit un Coach simple (champ `coach` de la séance). L'Admin n'anime pas de séance et n'apparaît pas dans la liste des coachs proposés.

## Paiement

L'application doit être prête à intégrer un système de paiement en ligne (ex. Stripe Checkout) ; pas encore implémenté.

**Première étape manuelle (implémentée)** : quand un membre consulte une séance ouverte aux inscriptions mais que son crédit est insuffisant pour réserver (ou pour rejoindre la liste d'attente), une carte remplace le bouton habituel et l'invite à régler son prochain carnet par **Wero** auprès du coach gestionnaire qui réceptionne les paiements (nom et téléphone configurés via `.env`, boutons "Copier" comme pour les canaux ntfy). Le gestionnaire crédite ensuite manuellement le compte une fois le paiement reçu (ajustement `+10`/`+1` existant sur la fiche membre) ; il n'y a pas encore d'intégration API Wero (pas disponible pour les marchands français à ce jour).

## Offres

Le catalogue des offres est **évolutif** : le coach gestionnaire (ou l'admin) peut créer, modifier ou supprimer une offre directement depuis l'application (boutons visibles sur la page `/offres/` pour eux uniquement — suppression refusée si des achats y sont déjà rattachés, la désactivation étant alors recommandée à la place). Catalogue actuel (4 offres de type carnet, page publique `/offres/`) :

- **1 séance** — 10 € — achat à l'unité, ne prolonge pas la date de péremption du solde
- **10 séances + 1 offerte** (11 au total) — 100 € — prolonge la péremption du solde de **3 mois**
- **20 séances + 3 offertes** (23 au total) — 200 € — prolonge la péremption du solde de **6 mois**
- **25 séances + 5 offertes** (30 au total) — 250 € — prolonge la péremption du solde de **6 mois**

Restent à implémenter comme offres à part entière (pour l'instant seul le mécanisme du pool partagé existe, voir « Familles ») :
- Une offre **famille**
- Des offres **personnalisées** (en prévoir 2 au début)

## Familles

Un membre peut être rattaché à une **famille**, qui regroupe plusieurs membres liés (ex. un foyer) :

- Le crédit de séances de l'offre famille est **partagé** entre tous les membres de la famille : une séance est décomptée du même pool, quel que soit le membre lié qui s'inscrit.
- La **tolérance de séances négatives** est définie au niveau de la famille (pas individuellement par membre) et s'applique de la même façon à tous les membres liés, pour éviter toute ambiguïté entre membres d'une même famille.

## Calendrier des séances

- Exposition d'un calendrier des séances
- Nombre maximum de participants fixé par le créateur de la séance (gestionnaire/coach ou admin)
- Des **modèles de séance type** disponibles

### Ouverture des inscriptions

- Les inscriptions à une séance n'ouvrent qu'à partir du **mercredi de la semaine précédant** celle de la séance
- Avant cette date, la séance est visible sur le calendrier mais l'inscription (et la liste d'attente) n'est pas possible
- Les membres sont notifiés à l'**ouverture des inscriptions** (et non à la création de la séance par le gestionnaire, qui peut avoir lieu bien avant)

### Vue calendrier

- Représentation graphique de l'occupation des séances, en vue **calendrier hebdomadaire**
- Navigation en avant / en arrière
- Accès à une **vue journalière** et une **vue par séance**
- Depuis cette vue, le membre peut s'inscrire ou se désinscrire
- Affichage de la liste des participants déjà inscrits ainsi que du coach de la séance

### Annulation d'une séance par le gestionnaire

- Si une séance n'a pas atteint un minimum de **4 participants** inscrits, le gestionnaire (ou l'admin) peut l'annuler
- Les membres inscrits sont notifiés (push ntfy, canal partagé membres — le seuil de 4 participants minimum n'est pour l'instant pas vérifié techniquement avant suppression, c'est une règle d'usage)
- Leur crédit de séance est restauré (recrédité), sans impact sur leurs jokers

## Gestion des séances achetées

- Gestion de l'achat de séances et du nombre de séances restantes disponibles (pour l'instant géré par l'admin ou le gestionnaire)
- Tant que le paiement en ligne n'est pas implémenté, c'est le gestionnaire ou l'admin qui met à jour :
  - les informations de paiement
  - le nombre de séances achetées
- Les dates d'achat de séances sont suivies par membre (modèle `Achat`, lié à l'offre choisie)
- Chaque achat (hors achat à l'unité) **prolonge** la date de péremption globale du solde de la durée de validité propre à l'offre achetée (3 ou 6 mois selon l'offre, voir « Offres ») — à partir de la péremption existante si elle est encore dans le futur, sinon à partir d'aujourd'hui. Prolongeable aussi manuellement à la discrétion du gestionnaire (ex. en cas de blessure)
- Sur la fiche membre, le gestionnaire/admin choisit une offre dans le catalogue pour enregistrer un achat (nombre de séances et durée de validité appliqués automatiquement ; prix payé modifiable pour une remise ponctuelle), et dispose aussi de boutons **+1** / **−1** pour des corrections manuelles ponctuelles
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
- En cas de désistement, le membre le plus haut dans la file est **automatiquement inscrit** — mais uniquement si la séance a lieu dans **plus de 24 h** ; passé ce délai, un désistement ne déclenche plus de promotion automatique
- Il est alerté par notification push (ntfy, canal partagé membres)
- Une fois inscrit automatiquement, il devient un membre inscrit à part entière : les règles communes s'appliquent, y compris la règle de désinscription tardive — s'il ne peut plus assister, il doit se désinscrire dans les délais, sous peine d'entamer son crédit joker

## Gestion des membres

- Le gestionnaire ou l'admin peut créer un compte membre (nom, prénom, email — obligatoire —, téléphone, tolérance). Aucun mot de passe initial à saisir : le compte est créé sans mot de passe utilisable, et un email est envoyé au membre avec un lien sécurisé pour qu'il définisse lui-même son mot de passe
- Le gestionnaire ou l'admin peut **désactiver** un membre plutôt que le supprimer : la connexion est bloquée mais son historique (inscriptions, achats, mouvements) est conservé ; la désactivation est réversible
- Le gestionnaire ou l'admin peut aussi **supprimer définitivement** un compte (doublon, erreur de saisie à la création...). Si le compte a une activité réelle (achats, inscriptions, séances animées), un avertissement le déconseille et recommande la désactivation à la place, mais la décision finale reste au gestionnaire : un bouton « Forcer la suppression » permet de supprimer quand même, avec effacement définitif de l'historique associé (cascade)

## Droits d'accès

- Un membre seul peut s'inscrire ou se désinscrire lui-même
- L'administrateur ou le gestionnaire ont tous les droits

## Notifications

Deux canaux : **email** et **push (ntfy.sh)**, gérables par chaque utilisateur depuis l'onglet « Notifications ».

**Emails** — chaque type est activable/désactivable indépendamment par le membre (page Notifications) :
- Ouverture des inscriptions à une séance — *implémenté*
- Désinscription, joker utilisé, solde bas, crédit renouvelé, etc. — *à ajouter au fur et à mesure, même mécanisme*

Le mot de passe oublié (et l'email de définition de mot de passe à la création d'un compte) sont **toujours envoyés**, indépendamment de ces réglages — non désactivables.

**Push (ntfy.sh)** :
- Canal partagé pour tous les membres : ouverture des inscriptions, annulation de séance
- Canal **individuel** généré automatiquement pour chaque coach/coach gestionnaire/admin (topic aléatoire non devinable) — chacun choisit, événement par événement, s'il est notifié : inscription, désinscription, promotion automatique depuis la liste d'attente, séance complète. Un coach simple n'est notifié que pour ses propres séances ; un coach gestionnaire/admin peut suivre les séances d'autres coachs de son choix (rien coché = aucun autre coach que lui-même)

## Design

Structure et parcours UX (vue calendrier hebdomadaire, navigation par pastilles de jour, cards) inspirés de l'application **peppy.cool**.

L'habillage graphique (logo, couleurs) suit en revanche l'identité réelle du Garage, de style street-workout/graffiti :
- Noir : `#201e1f`
- Vert accent : `#80b048`

Fond sombre (noir) par défaut sur toutes les pages, texte clair — les cartes (contenu, formulaires) restent sur fond clair avec texte sombre. Icône de l'application (onglet navigateur, écran d'accueil mobile) : monogramme « G » vert sur fond noir.
