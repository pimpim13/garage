import csv

from django.utils import timezone

COLONNES = ['Date', 'Membre', 'Type', 'Description', 'Variation']
DEBUTS_FORMULE = ('=', '+', '-', '@')


def _neutraliser(valeur):
    """Empêche un tableur d'interpréter du texte saisi librement (ex. un nom) comme une formule."""
    return f"'{valeur}" if valeur.startswith(DEBUTS_FORMULE) else valeur


def lignes_export(mouvements_seances, mouvements_jokers):
    """Fusionne séances et jokers en lignes CSV, du plus récent au plus ancien."""
    elements = [('Séance', m) for m in mouvements_seances] + [('Joker', m) for m in mouvements_jokers]
    elements.sort(key=lambda element: element[1].horodatage, reverse=True)
    return [
        [
            timezone.localtime(mouvement.horodatage).strftime('%d/%m/%Y %H:%M'),
            _neutraliser(str(mouvement.membre)),
            type_mouvement,
            _neutraliser(mouvement.libelle),
            f"{mouvement.delta:+d}",
        ]
        for type_mouvement, mouvement in elements
    ]


def ecrire_csv(reponse, lignes):
    reponse.write('﻿')  # BOM : Excel reconnaît l'UTF-8 et affiche correctement les accents
    writer = csv.writer(reponse, delimiter=';')
    writer.writerow(COLONNES)
    writer.writerows(lignes)
    return reponse
