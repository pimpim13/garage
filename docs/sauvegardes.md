# Sauvegardes de la base de données

## Principe

1. Chaque nuit à 3h, le cron lance `scripts/backup_db.sh` : copie cohérente de `db.sqlite3` dans `/opt/garage/backups/` (10 dernières conservées).
2. Si `BACKUP_RCLONE_REMOTE` est défini, la même copie est envoyée **chiffrée** sur Google Drive via `rclone` (30 jours conservés à distance).
3. Si l'envoi échoue, le script sort en erreur (visible dans `backup.log`) et, si `NTFY_TOPIC_ALERTES` est défini, envoie une alerte ntfy.

Sans `BACKUP_RCLONE_REMOTE`, le comportement reste celui d'avant (sauvegarde locale seule).

> La base contient des données personnelles (noms, emails, téléphones) : elle ne doit jamais partir en clair vers un cloud. D'où le remote `crypt`.

## Mise en place (une seule fois)

### 1. Installer rclone sur le serveur

```bash
sudo apt install rclone      # ou : curl https://rclone.org/install.sh | sudo bash
```

### 2. Autoriser l'accès à Google Drive

Le serveur n'a pas de navigateur : l'autorisation se fait depuis un poste qui en a un (Mac).

Sur le Mac (`brew install rclone`) :

```bash
rclone authorize "drive" "--drive-scope=drive.file"
```

Une page Google s'ouvre ; après validation, le terminal affiche un jeton `{"access_token":...}` à copier.

Sur le serveur :

```bash
rclone config
# n) New remote   -> nom : garage-drive
# Storage         -> drive (Google Drive)
# client_id / client_secret : laisser vide (ou voir « Pièges » ci-dessous)
# scope           -> 3 (drive.file : accès limité aux fichiers créés par rclone)
# Use auto config -> n
# result> coller le jeton copié sur le Mac
```

`drive.file` est volontaire : le serveur ne peut ni lire ni supprimer le reste du Drive.

### 3. Ajouter le chiffrement par-dessus

```bash
rclone config
# n) New remote   -> nom : garage-crypt
# Storage         -> crypt
# remote          -> garage-drive:Sauvegardes-Garage
# filename_encryption -> standard
# Password        -> g (générer) puis noter le mot de passe
# Salt            -> g (générer) puis noter le sel
```

**Conserver le mot de passe ET le sel hors du serveur** (gestionnaire de mots de passe). Sans eux, les sauvegardes sont définitivement illisibles, y compris si le serveur est perdu, ce qui est justement le cas à couvrir.

### 4. Activer l'envoi

Dans `/opt/garage/.env` :

```
BACKUP_RCLONE_REMOTE=garage-crypt:
NTFY_TOPIC_ALERTES=<topic ntfy privé, difficile à deviner>
```

S'abonner à ce topic dans l'appli ntfy du téléphone pour recevoir les alertes. Le cron existant n'a pas à changer.

### 5. Tester

```bash
/opt/garage/scripts/backup_db.sh
rclone ls garage-crypt:            # le fichier doit apparaître (en clair via crypt)
rclone ls garage-drive:Sauvegardes-Garage   # côté Drive : noms illisibles = chiffrement actif
```

Provoquer une panne (ex. `BACKUP_RCLONE_REMOTE=inexistant:`) pour vérifier que l'alerte arrive.

## Restaurer

Sur n'importe quelle machine disposant de rclone et de la configuration `garage-crypt` (mot de passe + sel) :

```bash
rclone ls garage-crypt:
rclone copyto garage-crypt:db_2026-10-07_030000.sqlite3 ./db_restauree.sqlite3
sqlite3 db_restauree.sqlite3 "PRAGMA integrity_check; SELECT count(*) FROM accounts_user;"
```

Pour remettre en service : arrêter l'appli, remplacer `/opt/garage/db.sqlite3` par le fichier restauré, relancer. **Faire une restauration d'essai sur une machine de test après la mise en place**, puis de temps en temps : une sauvegarde jamais restaurée n'est pas une garantie.

## Pièges connus

- **Jeton qui expire** : avec un `client_id` Google personnel dont l'application est en mode « Test », le jeton expire après 7 jours. Soit utiliser le client rclone par défaut (limites partagées, suffisant pour un fichier par nuit), soit passer l'application « En production » dans la console Google Cloud.
- **Surveillance** : vérifier de temps en temps `/opt/garage/backups/backup.log` et la présence de fichiers récents sur Drive.
- **Quota** : la base fait quelques Mo ; 30 copies restent très en dessous des 15 Go gratuits.
