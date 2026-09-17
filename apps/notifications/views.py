from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.models import User

from .ntfy import notifier_coach, notifier_membres

CHAMPS_PREFERENCE_EVENEMENTS = [
    'notifie_inscription',
    'notifie_desinscription',
    'notifie_promotion_automatique',
    'notifie_seance_complete',
]

CHAMPS_PREFERENCE_EMAILS = [
    'email_ouverture_seance',
]


@login_required
def preferences(request):
    context = {}

    if request.user.is_membre:
        if request.method == 'POST':
            for champ in CHAMPS_PREFERENCE_EMAILS:
                setattr(request.user, champ, champ in request.POST)
            request.user.save(update_fields=CHAMPS_PREFERENCE_EMAILS)
            messages.success(request, "Préférences de notification mises à jour.")
            return redirect('notifications:preferences')
        for champ in CHAMPS_PREFERENCE_EMAILS:
            context[champ] = getattr(request.user, champ)
        context['topic_ntfy_membres'] = settings.NTFY_TOPIC_MEMBRES

    if request.user.anime_des_seances:
        if request.method == 'POST':
            for champ in CHAMPS_PREFERENCE_EVENEMENTS:
                setattr(request.user, champ, champ in request.POST)
            request.user.save(update_fields=CHAMPS_PREFERENCE_EVENEMENTS)
            if request.user.is_staff_or_manager:
                ids = [i for i in request.POST.getlist('coachs_suivis') if i.isdigit()]
                request.user.coachs_suivis.set(User.objects.filter(pk__in=ids))
            messages.success(request, "Préférences de notification mises à jour.")
            return redirect('notifications:preferences')

        context['topic_ntfy_coach'] = request.user.topic_ntfy_coach
        for champ in CHAMPS_PREFERENCE_EVENEMENTS:
            context[champ] = getattr(request.user, champ)
        if request.user.is_staff_or_manager:
            context['est_gestionnaire_ou_admin'] = True
            context['coachs_disponibles'] = User.objects.filter(
                role__in=[User.Role.GESTIONNAIRE, User.Role.COACH]
            ).exclude(pk=request.user.pk)
            context['coachs_suivis_ids'] = set(request.user.coachs_suivis.values_list('pk', flat=True))

    return render(request, 'notifications/preferences.html', context)


@login_required
@require_POST
def tester_notification(request):
    canal = request.POST.get('canal')
    if canal == 'membre' and request.user.is_membre:
        notifier_membres("Ceci est une notification de test envoyée depuis Le Garage.")
        messages.success(request, "Notification de test envoyée sur le canal membres.")
    elif canal == 'coach' and request.user.anime_des_seances:
        notifier_coach(request.user, "Ceci est une notification de test envoyée depuis Le Garage.")
        messages.success(request, "Notification de test envoyée sur ton canal personnel.")
    else:
        messages.error(request, "Impossible d'envoyer une notification de test.")
    return redirect('notifications:preferences')
