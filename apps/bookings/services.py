from dateutil.relativedelta import relativedelta
from django.db.models import Sum
from django.utils import timezone

from apps.notifications.ntfy import notifier_coachs, notifier_membres
from apps.purchases.models import MouvementSeance
from apps.purchases.services import solde_seances

from .models import Inscription, MouvementJoker

JOKER_MAX = 1
DELAI_REACQUISITION_JOKER = relativedelta(months=3)


def peut_s_inscrire(membre):
    return solde_seances(membre) - 1 >= -membre.tolerance_applicable


def solde_jokers(membre):
    total = MouvementJoker.objects.filter(membre=membre).aggregate(total=Sum('delta'))['total']
    return total or 0


def historique_jokers(membre):
    return MouvementJoker.objects.filter(membre=membre).select_related(
        'auteur', 'inscription__seance'
    ).order_by('-horodatage')


def _consommer_joker(membre, auteur, inscription=None, commentaire=''):
    MouvementJoker.objects.create(
        membre=membre,
        delta=-1,
        motif=MouvementJoker.Motif.UTILISATION,
        inscription=inscription,
        auteur=auteur,
        commentaire=commentaire,
    )
    membre.date_reacquisition_joker = timezone.localdate() + DELAI_REACQUISITION_JOKER
    membre.save(update_fields=['date_reacquisition_joker'])


def attribuer_joker_initial(membre):
    MouvementJoker.objects.create(membre=membre, delta=1, motif=MouvementJoker.Motif.ATTRIBUTION)


def attribuer_joker(membre, auteur, commentaire=''):
    if solde_jokers(membre) >= JOKER_MAX:
        raise ValueError("Ce membre a déjà un joker disponible.")
    MouvementJoker.objects.create(
        membre=membre,
        delta=1,
        motif=MouvementJoker.Motif.ATTRIBUTION,
        auteur=auteur,
        commentaire=commentaire,
    )
    membre.date_reacquisition_joker = None
    membre.save(update_fields=['date_reacquisition_joker'])


def retirer_joker(membre, auteur, commentaire=''):
    if solde_jokers(membre) < 1:
        raise ValueError("Ce membre n'a pas de joker disponible.")
    _consommer_joker(membre, auteur, commentaire=commentaire)


def marquer_non_presente(inscription, auteur, commentaire=''):
    membre = inscription.membre
    inscription.statut = Inscription.Statut.NON_PRESENTE
    inscription.save(update_fields=['statut'])
    if solde_jokers(membre) >= 1:
        _consommer_joker(membre, auteur, inscription=inscription, commentaire=commentaire)


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
    membre = inscription.membre
    seance = inscription.seance
    tardive = seance.desinscription_tardive
    avec_joker = tardive and solde_jokers(membre) >= 1

    if tardive:
        inscription.statut = (
            Inscription.Statut.DESINSCRIT_TARDIF_JOKER if avec_joker else Inscription.Statut.DESINSCRIT_TARDIF_SANS_JOKER
        )
    else:
        inscription.statut = Inscription.Statut.DESINSCRIT
    inscription.desinscrit_le = timezone.now()
    inscription.auteur = auteur
    inscription.save(update_fields=['statut', 'desinscrit_le', 'auteur'])

    if avec_joker:
        _consommer_joker(membre, auteur, inscription=inscription)
        MouvementSeance.objects.create(
            membre=membre,
            delta=1,
            motif=MouvementSeance.Motif.DESINSCRIPTION_TARDIVE_JOKER,
            inscription=inscription,
            auteur=auteur,
        )
    elif tardive:
        MouvementSeance.objects.create(
            membre=membre,
            delta=0,
            motif=MouvementSeance.Motif.DESINSCRIPTION_TARDIVE_SANS_JOKER,
            inscription=inscription,
            auteur=auteur,
        )
    else:
        MouvementSeance.objects.create(
            membre=membre,
            delta=1,
            motif=MouvementSeance.Motif.DESINSCRIPTION,
            inscription=inscription,
            auteur=auteur,
        )
    promouvoir_liste_attente(seance)


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
