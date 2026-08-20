from django.db.models import Sum
from django.utils import timezone

from .models import MouvementSeance


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
