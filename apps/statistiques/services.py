import calendar
import datetime
from collections import defaultdict
from dataclasses import dataclass

from django.db.models import Count, Q
from django.utils import timezone

from apps.bookings.models import Inscription
from apps.scheduling.models import Seance

SEUIL_MINIMUM_PARTICIPANTS = 4
SEUIL_EVOLUTION_MENSUELLE_JOURS = 120
JOURS_SEMAINE = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
MOIS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.']

# Un membre « occupe une place » s'il est inscrit (présent) ou inscrit mais non présenté.
# Les désinscrits (même tardifs), permutés et la liste d'attente libèrent la place.
STATUTS_PLACE_OCCUPEE = [Inscription.Statut.INSCRIT, Inscription.Statut.NON_PRESENTE]


@dataclass
class Filtres:
    debut: datetime.date
    fin: datetime.date
    nom: str = ''
    coach_id: int | None = None


def resoudre_periode(preset, debut_str, fin_str, aujourd_hui):
    """Retourne (début, fin) inclus pour un préréglage de période ; le mois en cours par défaut."""
    if preset == 'semaine':
        lundi = aujourd_hui - datetime.timedelta(days=aujourd_hui.weekday())
        return lundi, lundi + datetime.timedelta(days=6)
    if preset == 'trimestre':
        mois_debut = 3 * ((aujourd_hui.month - 1) // 3) + 1
        dernier = calendar.monthrange(aujourd_hui.year, mois_debut + 2)[1]
        return (
            datetime.date(aujourd_hui.year, mois_debut, 1),
            datetime.date(aujourd_hui.year, mois_debut + 2, dernier),
        )
    if preset == 'annee':
        return datetime.date(aujourd_hui.year, 1, 1), datetime.date(aujourd_hui.year, 12, 31)
    if preset == 'perso':
        try:
            debut = datetime.date.fromisoformat(debut_str)
            fin = datetime.date.fromisoformat(fin_str)
        except ValueError:
            pass
        else:
            return (debut, fin) if debut <= fin else (fin, debut)
    dernier = calendar.monthrange(aujourd_hui.year, aujourd_hui.month)[1]
    return datetime.date(aujourd_hui.year, aujourd_hui.month, 1), datetime.date(
        aujourd_hui.year, aujourd_hui.month, dernier
    )


def noms_de_seances():
    return list(Seance.objects.order_by('nom').values_list('nom', flat=True).distinct())


def _pourcentage(numerateur, denominateur):
    return round(100 * numerateur / denominateur, 1) if denominateur else 0


def _seances_de_la_periode(filtres, maintenant):
    debut = timezone.make_aware(datetime.datetime.combine(filtres.debut, datetime.time.min))
    fin = timezone.make_aware(datetime.datetime.combine(filtres.fin + datetime.timedelta(days=1), datetime.time.min))
    seances = Seance.objects.filter(debut__gte=debut, debut__lt=min(fin, maintenant)).select_related('coach')
    if filtres.nom:
        seances = seances.filter(nom=filtres.nom)
    if filtres.coach_id:
        seances = seances.filter(coach_id=filtres.coach_id)
    return seances.annotate(
        nb_inscrits=Count('inscriptions', filter=Q(inscriptions__statut__in=STATUTS_PLACE_OCCUPEE))
    )


def _libelle_coach(coach):
    if coach is None:
        return 'Sans coach'
    return coach.first_name or coach.get_full_name() or coach.username


def _ventiler(seances, cle_et_libelle):
    groupes = defaultdict(lambda: {'seances': 0, 'inscrits': 0, 'capacite': 0, 'sous_seuil': 0})
    for seance in seances:
        groupe = groupes[cle_et_libelle(seance)]
        groupe['seances'] += 1
        groupe['inscrits'] += seance.nb_inscrits
        groupe['capacite'] += seance.capacite_max
        groupe['sous_seuil'] += seance.nb_inscrits < SEUIL_MINIMUM_PARTICIPANTS
    lignes = [
        {'libelle': libelle, **g, 'remplissage': _pourcentage(g['inscrits'], g['capacite']),
         'moyenne_inscrits': round(g['inscrits'] / g['seances'], 1)}
        for libelle, g in groupes.items()
    ]
    return sorted(lignes, key=lambda l: (-l['inscrits'], l['libelle']))


def _debut_de_periode(jour, mensuelle):
    return jour.replace(day=1) if mensuelle else jour - datetime.timedelta(days=jour.weekday())


def _periode_suivante(jour, mensuelle):
    if mensuelle:
        return (jour.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
    return jour + datetime.timedelta(days=7)


def _evolution(seances, filtres):
    mensuelle = (filtres.fin - filtres.debut).days > SEUIL_EVOLUTION_MENSUELLE_JOURS
    cles = []
    courant = _debut_de_periode(filtres.debut, mensuelle)
    while courant <= filtres.fin:
        cles.append(courant)
        courant = _periode_suivante(courant, mensuelle)
    nb_seances = dict.fromkeys(cles, 0)
    inscrits = dict.fromkeys(cles, 0)
    capacite = dict.fromkeys(cles, 0)
    for seance in seances:
        cle = _debut_de_periode(timezone.localtime(seance.debut).date(), mensuelle)
        if cle in nb_seances:
            nb_seances[cle] += 1
            inscrits[cle] += seance.nb_inscrits
            capacite[cle] += seance.capacite_max
    libelle = (lambda c: f"{MOIS[c.month - 1]} {c.year}") if mensuelle else (lambda c: f"{c:%d/%m}")
    return {
        'granularite': 'mois' if mensuelle else 'semaine',
        'libelles': [libelle(c) for c in cles],
        'seances': [nb_seances[c] for c in cles],
        'inscrits': [inscrits[c] for c in cles],
        'remplissage': [_pourcentage(inscrits[c], capacite[c]) for c in cles],
    }


def _heatmap(seances):
    creneaux = defaultdict(lambda: {'seances': 0, 'inscrits': 0, 'capacite': 0})
    for seance in seances:
        debut = timezone.localtime(seance.debut)
        creneau = creneaux[(debut.hour, debut.weekday())]
        creneau['seances'] += 1
        creneau['inscrits'] += seance.nb_inscrits
        creneau['capacite'] += seance.capacite_max
    heures = sorted({heure for heure, _ in creneaux})
    cases = {
        heure: [
            (
                {'seances': c['seances'], 'remplissage': _pourcentage(c['inscrits'], c['capacite'])}
                if (c := creneaux.get((heure, jour))) else None
            )
            for jour in range(7)
        ]
        for heure in heures
    }
    return {'heures': heures, 'jours': JOURS_SEMAINE, 'cases': cases}


def calculer(filtres, maintenant=None):
    maintenant = maintenant or timezone.now()
    seances = list(_seances_de_la_periode(filtres, maintenant))
    inscrits = sum(s.nb_inscrits for s in seances)
    capacite = sum(s.capacite_max for s in seances)
    return {
        'synthese': {
            'seances': len(seances),
            'inscrits': inscrits,
            'remplissage': _pourcentage(inscrits, capacite),
            'moyenne_inscrits': round(inscrits / len(seances), 1) if seances else 0,
            'sous_seuil': sum(s.nb_inscrits < SEUIL_MINIMUM_PARTICIPANTS for s in seances),
        },
        'par_type': _ventiler(seances, lambda s: s.nom),
        'par_coach': _ventiler(seances, lambda s: _libelle_coach(s.coach)),
        'sous_seuil': [
            {'seance': s, 'inscrits': s.nb_inscrits}
            for s in sorted(seances, key=lambda s: s.debut, reverse=True)
            if s.nb_inscrits < SEUIL_MINIMUM_PARTICIPANTS
        ],
        'evolution': _evolution(seances, filtres),
        'heatmap': _heatmap(seances),
    }
