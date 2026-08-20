from dateutil.relativedelta import relativedelta
from django.db.models import Sum
from django.utils import timezone

from .models import Achat, MouvementSeance


def solde_seances(membre):
    date_expiration = membre.date_expiration_applicable
    if date_expiration and date_expiration < timezone.localdate():
        return 0

    if membre.famille_id:
        mouvements = MouvementSeance.objects.filter(membre__famille=membre.famille)
    else:
        mouvements = MouvementSeance.objects.filter(membre=membre)
    total = mouvements.aggregate(total=Sum('delta'))['total']
    return total or 0


def _prolonger_expiration(membre):
    titulaire = membre.famille if membre.famille_id else membre
    aujourdhui = timezone.localdate()
    date_actuelle = titulaire.date_expiration_solde
    base = max(date_actuelle, aujourdhui) if date_actuelle else aujourdhui
    titulaire.date_expiration_solde = base + relativedelta(months=6)
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
    _prolonger_expiration(membre)
    return achat
