from django.utils import timezone

from apps.notifications.ntfy import notifier_coachs, notifier_membres
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
    promouvoir_liste_attente(inscription.seance)


def promouvoir_liste_attente(seance):
    if not seance.promotion_liste_attente_possible or seance.places_restantes <= 0:
        return None

    candidats = seance.inscriptions.filter(statut=Inscription.Statut.EN_ATTENTE).order_by('inscrit_le')
    for candidat in candidats:
        if not peut_s_inscrire(candidat.membre):
            continue
        candidat.statut = Inscription.Statut.INSCRIT
        candidat.save(update_fields=['statut'])
        MouvementSeance.objects.create(
            membre=candidat.membre,
            delta=-1,
            motif=MouvementSeance.Motif.INSCRIPTION,
            inscription=candidat,
            auteur=candidat.auteur,
        )
        debut = timezone.localtime(seance.debut)
        notifier_membres(
            f"{candidat.membre} inscrit(e) automatiquement à « {seance.nom} » le {debut:%d/%m à %H:%M} "
            "(désistement)."
        )
        notifier_coachs(
            f"{candidat.membre} inscrit(e) automatiquement à « {seance.nom} » le {debut:%d/%m à %H:%M} "
            "(liste d'attente)."
        )
        return candidat
    return None
