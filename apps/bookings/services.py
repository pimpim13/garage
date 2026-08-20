from django.utils import timezone

from apps.purchases.models import MouvementSeance
from apps.purchases.services import solde_seances

from .models import Inscription


def peut_s_inscrire(membre):
    return solde_seances(membre) - 1 >= -membre.tolerance_applicable


def enregistrer_inscription(membre, seance, auteur):
    inscription = Inscription.objects.create(membre=membre, seance=seance, auteur=auteur)
    MouvementSeance.objects.create(
        membre=membre,
        delta=-1,
        motif=MouvementSeance.Motif.INSCRIPTION,
        inscription=inscription,
        auteur=auteur,
    )
    return inscription


def enregistrer_desinscription(inscription, auteur):
    inscription.statut = Inscription.Statut.DESINSCRIT
    inscription.desinscrit_le = timezone.now()
    inscription.auteur = auteur
    inscription.save(update_fields=['statut', 'desinscrit_le', 'auteur'])
    MouvementSeance.objects.create(
        membre=inscription.membre,
        delta=1,
        motif=MouvementSeance.Motif.DESINSCRIPTION,
        inscription=inscription,
        auteur=auteur,
    )
