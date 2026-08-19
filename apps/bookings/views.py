from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.scheduling.models import Seance

from .models import Inscription


def _retour(request, seance):
    return request.POST.get('next') or reverse('scheduling:seance_detail', kwargs={'pk': seance.pk})


def _desinscrire(inscription, auteur):
    inscription.statut = Inscription.Statut.DESINSCRIT
    inscription.desinscrit_le = timezone.now()
    inscription.auteur = auteur
    inscription.save(update_fields=['statut', 'desinscrit_le', 'auteur'])


@login_required
@require_POST
def inscrire(request, seance_id):
    seance = get_object_or_404(Seance, pk=seance_id)
    if request.user.inscriptions.filter(seance=seance, statut=Inscription.Statut.INSCRIT).exists():
        messages.info(request, "Vous êtes déjà inscrit(e) à cette séance.")
    elif seance.places_restantes <= 0:
        messages.error(request, "Cette séance est complète.")
    else:
        Inscription.objects.create(membre=request.user, seance=seance, auteur=request.user)
        messages.success(request, "Inscription confirmée.")
    return redirect(_retour(request, seance))


@login_required
@require_POST
def desinscrire(request, seance_id):
    seance = get_object_or_404(Seance, pk=seance_id)
    inscription = request.user.inscriptions.filter(
        seance=seance, statut=Inscription.Statut.INSCRIT
    ).first()
    if inscription is None:
        messages.info(request, "Vous n'étiez pas inscrit(e) à cette séance.")
    else:
        _desinscrire(inscription, request.user)
        messages.success(request, "Désinscription confirmée.")
    return redirect(_retour(request, seance))


@login_required
@require_POST
def liste_attente_rejoindre(request, seance_id):
    seance = get_object_or_404(Seance, pk=seance_id)
    deja_actif = request.user.inscriptions.filter(
        seance=seance, statut__in=[Inscription.Statut.INSCRIT, Inscription.Statut.EN_ATTENTE]
    ).exists()
    if deja_actif:
        messages.info(request, "Vous êtes déjà inscrit(e) ou en liste d'attente pour cette séance.")
    elif seance.places_restantes > 0:
        messages.info(request, "Cette séance a encore de la place, vous pouvez vous inscrire directement.")
    else:
        Inscription.objects.create(
            membre=request.user, seance=seance, auteur=request.user, statut=Inscription.Statut.EN_ATTENTE
        )
        messages.success(request, "Vous êtes positionné(e) en liste d'attente.")
    return redirect(_retour(request, seance))


@login_required
@require_POST
def liste_attente_quitter(request, seance_id):
    seance = get_object_or_404(Seance, pk=seance_id)
    inscription = request.user.inscriptions.filter(
        seance=seance, statut=Inscription.Statut.EN_ATTENTE
    ).first()
    if inscription is None:
        messages.info(request, "Vous n'étiez pas en liste d'attente pour cette séance.")
    else:
        _desinscrire(inscription, request.user)
        messages.success(request, "Vous avez quitté la liste d'attente.")
    return redirect(_retour(request, seance))


@login_required
@require_POST
def inscrire_membre(request, seance_id):
    if not request.user.is_staff_or_manager:
        raise PermissionDenied
    seance = get_object_or_404(Seance, pk=seance_id)
    membre = get_object_or_404(User, pk=request.POST.get('membre_id'), role=User.Role.MEMBRE)
    if Inscription.objects.filter(membre=membre, seance=seance, statut=Inscription.Statut.INSCRIT).exists():
        messages.info(request, f"{membre} est déjà inscrit(e) à cette séance.")
    elif seance.places_restantes <= 0:
        messages.error(request, "Cette séance est complète.")
    else:
        Inscription.objects.create(membre=membre, seance=seance, auteur=request.user)
        messages.success(request, f"{membre} a été inscrit(e).")
    return redirect(_retour(request, seance))


@login_required
@require_POST
def desinscrire_membre(request, seance_id, membre_id):
    if not request.user.is_staff_or_manager:
        raise PermissionDenied
    seance = get_object_or_404(Seance, pk=seance_id)
    inscription = Inscription.objects.filter(
        membre_id=membre_id, seance=seance, statut=Inscription.Statut.INSCRIT
    ).first()
    if inscription is None:
        messages.info(request, "Ce membre n'était pas inscrit à cette séance.")
    else:
        membre = inscription.membre
        _desinscrire(inscription, request.user)
        messages.success(request, f"{membre} a été désinscrit(e).")
    return redirect(_retour(request, seance))
