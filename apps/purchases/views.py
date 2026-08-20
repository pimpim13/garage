from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.models import User

from .services import ajuster_solde, historique_seances, solde_seances, statut_solde

AJUSTEMENTS_AUTORISES = (10, 1, -1)


@login_required
def mon_solde(request):
    context = {
        'solde': solde_seances(request.user),
        'statut_solde': statut_solde(request.user),
        'historique': historique_seances(request.user),
    }
    return render(request, 'purchases/mon_solde.html', context)


@login_required
@require_POST
def ajuster_solde_membre(request, membre_id):
    if not request.user.is_staff_or_manager:
        raise PermissionDenied
    membre = get_object_or_404(User, pk=membre_id, role=User.Role.MEMBRE)
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
