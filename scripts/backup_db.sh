#!/usr/bin/env bash
# Sauvegarde la base SQLite du Garage et ne conserve que les N dernières sauvegardes en local.
# Si BACKUP_RCLONE_REMOTE est défini (variable d'environnement ou fichier .env), envoie aussi
# une copie hors du serveur (ex. Google Drive chiffré via rclone) : voir docs/sauvegardes.md.
set -euo pipefail

PROJET_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="$PROJET_DIR/db.sqlite3"
BACKUP_DIR="$PROJET_DIR/backups"
NB_A_CONSERVER=10
JOURS_A_CONSERVER_A_DISTANCE=30

# Lit une variable dans l'environnement, à défaut dans .env (cron ne charge pas le .env).
lire_config() {
  local nom="$1"
  if [ -n "${!nom:-}" ]; then
    echo "${!nom}"
    return
  fi
  [ -f "$PROJET_DIR/.env" ] || return 0
  { grep -E "^${nom}=" "$PROJET_DIR/.env" || true; } | tail -n 1 | cut -d= -f2- | sed -e 's/^["'\'']//' -e 's/["'\'']$//'
}

alerter() {
  local topic base
  topic="$(lire_config NTFY_TOPIC_ALERTES)"
  base="$(lire_config NTFY_BASE_URL)"
  [ -n "$topic" ] || return 0
  curl -fsS -H "Title: Le Garage - sauvegarde" -d "$1" "${base:-https://ntfy.sh}/${topic}" >/dev/null || true
}

envoyer_copie_distante() {
  local remote
  remote="$(lire_config BACKUP_RCLONE_REMOTE)"
  if [ -z "$remote" ]; then
    echo "Copie distante non configurée (BACKUP_RCLONE_REMOTE absent) : ignorée."
    return 0
  fi
  command -v rclone >/dev/null || { echo "rclone introuvable" >&2; return 1; }
  case "$remote" in *: ) ;; * ) remote="${remote%/}/" ;; esac

  # Vérifications explicites : appelée depuis un "if", la fonction n'hérite pas de "set -e".
  rclone copyto "$DESTINATION" "${remote}$(basename "$DESTINATION")" || return 1
  rclone delete "$remote" --min-age "${JOURS_A_CONSERVER_A_DISTANCE}d" || return 1
  echo "Copie distante effectuée : ${remote}"
}

if [ ! -f "$DB_PATH" ]; then
  echo "Base introuvable : $DB_PATH" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"

HORODATAGE="$(date +%Y-%m-%d_%H%M%S)"
DESTINATION="$BACKUP_DIR/db_${HORODATAGE}.sqlite3"

# ".backup" utilise l'API de sauvegarde SQLite : cohérent même si l'appli écrit en même temps,
# contrairement à un simple "cp".
sqlite3 "$DB_PATH" ".backup '${DESTINATION}'"

# Ne garde que les $NB_A_CONSERVER sauvegardes les plus récentes.
ls -1t "$BACKUP_DIR"/db_*.sqlite3 2>/dev/null | tail -n "+$((NB_A_CONSERVER + 1))" | while IFS= read -r fichier; do
  rm -f "$fichier"
done

echo "Sauvegarde effectuée : $DESTINATION"

if ! envoyer_copie_distante; then
  echo "ÉCHEC de la copie distante" >&2
  alerter "Échec de l'envoi de la sauvegarde hors serveur ($(date +%d/%m/%Y))."
  exit 1
fi
