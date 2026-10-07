import datetime
from collections import namedtuple

from dateutil.relativedelta import relativedelta
from django.db.models import Sum
from django.utils import timezone

from .models import Achat, MouvementSeance


def _mouvements_pour(membre):
    if membre.famille_id:
        return MouvementSeance.objects.filter(membre__famille=membre.famille)
    return MouvementSeance.objects.filter(membre=membre)


def solde_seances(membre):
    date_expiration = membre.date_expiration_applicable
    if date_expiration and date_expiration < timezone.localdate():
        return 0

    total = _mouvements_pour(membre).aggregate(total=Sum('delta'))['total']
    return total or 0


def statut_solde(membre):
    solde = solde_seances(membre)
    tolerance = membre.tolerance_applicable
    if solde > 0:
        return 'vert'
    if solde <= -tolerance:
        return 'rouge'
    return 'orange'


Periode = namedtuple('Periode', ['cle', 'debut', 'fin', 'libelle'])

LIBELLE_TOUT = "Tout l'historique"


def _date_ou_none(valeur):
    try:
        return datetime.date.fromisoformat(valeur)
    except (TypeError, ValueError):
        return None


def resoudre_periode(periode, du, au, aujourdhui=None):
    """Traduit le choix de période (tout / mois / semaine / perso) en bornes de dates incluses."""
    aujourdhui = aujourdhui or timezone.localdate()
    if periode == 'mois':
        debut = aujourdhui.replace(day=1)
        fin = debut + relativedelta(months=1, days=-1)
        return Periode('mois', debut, fin, 'Ce mois-ci')
    if periode == 'semaine':
        debut = aujourdhui - datetime.timedelta(days=aujourdhui.weekday())
        return Periode('semaine', debut, debut + datetime.timedelta(days=6), 'Cette semaine')
    if periode == 'perso':
        debut, fin = _date_ou_none(du), _date_ou_none(au)
        if debut and fin and debut > fin:
            debut, fin = fin, debut
        if debut and fin:
            return Periode('perso', debut, fin, f"Du {debut:%d/%m/%Y} au {fin:%d/%m/%Y}")
        if debut:
            return Periode('perso', debut, None, f"Depuis le {debut:%d/%m/%Y}")
        if fin:
            return Periode('perso', None, fin, f"Jusqu'au {fin:%d/%m/%Y}")
    return Periode('tout', None, None, LIBELLE_TOUT)


def filtrer_periode(queryset, debut=None, fin=None):
    if debut:
        queryset = queryset.filter(horodatage__date__gte=debut)
    if fin:
        queryset = queryset.filter(horodatage__date__lte=fin)
    return queryset


def historique_seances(membre, debut=None, fin=None):
    mouvements = _mouvements_pour(membre).select_related('membre', 'auteur', 'inscription__seance')
    return filtrer_periode(mouvements, debut, fin).order_by('-horodatage')


def ajuster_solde(membre, delta, auteur):
    return MouvementSeance.objects.create(
        membre=membre,
        delta=delta,
        motif=MouvementSeance.Motif.AJUSTEMENT,
        auteur=auteur,
    )


def _prolonger_expiration(membre, offre):
    if not offre.duree_validite_mois:
        return
    titulaire = membre.famille if membre.famille_id else membre
    aujourdhui = timezone.localdate()
    date_actuelle = titulaire.date_expiration_solde
    base = max(date_actuelle, aujourdhui) if date_actuelle else aujourdhui
    titulaire.date_expiration_solde = base + relativedelta(months=offre.duree_validite_mois)
    titulaire.save(update_fields=['date_expiration_solde'])


def enregistrer_achat(membre, offre, prix_paye, saisi_par):
    achat = Achat.objects.create(
        membre=membre,
        offre=offre,
        nombre_seances=offre.nombre_seances,
        prix_paye=prix_paye,
        statut_paiement=Achat.StatutPaiement.PAYE,
        saisi_par=saisi_par,
    )
    MouvementSeance.objects.create(
        membre=membre,
        delta=offre.nombre_seances,
        motif=MouvementSeance.Motif.ACHAT,
        achat=achat,
        auteur=saisi_par,
    )
    _prolonger_expiration(membre, offre)
    return achat
