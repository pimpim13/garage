from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.bookings.services import historique_jokers, solde_jokers
from apps.offers.models import Offre

from .export import ecrire_csv, lignes_export
from .services import (
    ajuster_solde, enregistrer_achat, historique_seances, resoudre_periode, solde_seances, statut_solde,
)

AJUSTEMENTS_AUTORISES = (1, -1)
ROLES_GERES = [User.Role.MEMBRE, User.Role.COACH, User.Role.GESTIONNAIRE]


def _periode(request):
    return resoudre_periode(request.GET.get('periode'), request.GET.get('du'), request.GET.get('au'))


def _jokers(membre, periode):
    return historique_jokers(membre, periode.debut, periode.fin) if membre.is_membre else None


def _contexte_historique(request, membre, titre=None):
    periode = _periode(request)
    return {
        'membre': membre,
        'titre': titre,
        'periode': periode,
        'solde': solde_seances(membre),
        'statut_solde': statut_solde(membre),
        'date_expiration': membre.date_expiration_applicable,
        'historique': historique_seances(membre, periode.debut, periode.fin),
        'solde_jokers': solde_jokers(membre),
        'date_reacquisition_joker': membre.date_reacquisition_joker,
        'historique_jokers': _jokers(membre, periode),
        'afficher_membre': bool(membre.famille_id),
        'imprime_le': timezone.localtime(),
    }


def _export_csv(request, membre):
    periode = _periode(request)
    jokers = _jokers(membre, periode) or []
    reponse = HttpResponse(content_type='text/csv; charset=utf-8')
    nom_fichier = f"historique-{slugify(str(membre)) or membre.pk}-{timezone.localdate():%Y%m%d}.csv"
    reponse['Content-Disposition'] = f'attachment; filename="{nom_fichier}"'
    lignes = lignes_export(historique_seances(membre, periode.debut, periode.fin), jokers)
    return ecrire_csv(reponse, lignes)


@login_required
def mon_solde(request):
    return render(request, 'purchases/mon_solde.html', _contexte_historique(request, request.user))


@login_required
def export_mon_solde(request):
    return _export_csv(request, request.user)


@login_required
def historique_membre(request, membre_id):
    if not request.user.is_staff_or_manager:
        raise PermissionDenied
    membre = get_object_or_404(User, pk=membre_id, role__in=ROLES_GERES)
    context = _contexte_historique(request, membre, titre=f"Historique de {membre}")
    return render(request, 'purchases/mon_solde.html', context)


@login_required
def export_historique_membre(request, membre_id):
    if not request.user.is_staff_or_manager:
        raise PermissionDenied
    membre = get_object_or_404(User, pk=membre_id, role__in=ROLES_GERES)
    return _export_csv(request, membre)


@login_required
@require_POST
def ajuster_solde_membre(request, membre_id):
    if not request.user.is_staff_or_manager:
        raise PermissionDenied
    membre = get_object_or_404(User, pk=membre_id, role__in=ROLES_GERES)
    try:
        delta = int(request.POST.get('delta'))
    except (TypeError, ValueError):
        delta = None
    if delta not in AJUSTEMENTS_AUTORISES:
        messages.error(request, "Ajustement invalide.")
    else:
        ajuster_solde(membre=membre, delta=delta, auteur=request.user)
        messages.success(request, f"Solde de {membre} ajusté de {delta:+d}.")
    return redirect(request.POST.get('next') or 'accounts:membre_liste')


@login_required
@require_POST
def enregistrer_achat_membre(request, membre_id):
    if not request.user.is_staff_or_manager:
        raise PermissionDenied
    membre = get_object_or_404(User, pk=membre_id, role__in=ROLES_GERES)
    offre = get_object_or_404(Offre, pk=request.POST.get('offre'), active=True)
    try:
        prix_paye = Decimal(request.POST.get('prix_paye'))
    except (TypeError, InvalidOperation):
        prix_paye = None
    if prix_paye is None or prix_paye < 0:
        messages.error(request, "Prix payé invalide.")
    else:
        enregistrer_achat(membre=membre, offre=offre, prix_paye=prix_paye, saisi_par=request.user)
        messages.success(request, f"Achat « {offre.nom} » enregistré pour {membre}.")
    return redirect(request.POST.get('next') or 'accounts:membre_liste')
