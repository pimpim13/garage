#!/usr/bin/env bash
# Sauvegarde la base SQLite du Garage et ne conserve que les N dernières sauvegardes.
set -euo pipefail

PROJET_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="$PROJET_DIR/db.sqlite3"
BACKUP_DIR="$PROJET_DIR/backups"
NB_A_CONSERVER=10

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
