from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import PreferenceNotification, TypeEvenement


@login_required
def preferences(request):
    context = {}

    if request.user.is_membre:
        preference, _ = PreferenceNotification.objects.get_or_create(
            membre=request.user,
            type_evenement=TypeEvenement.NOUVELLE_SEANCE,
            canal=PreferenceNotification.Canal.EMAIL,
            defaults={'active': True},
        )
        if request.method == 'POST':
            preference.active = 'recevoir_email_ouverture' in request.POST
            preference.save(update_fields=['active'])
            messages.success(request, "Préférences de notification mises à jour.")
            return redirect('notifications:preferences')
        context['recevoir_email_ouverture'] = preference.active
        context['topic_ntfy_membres'] = settings.NTFY_TOPIC_MEMBRES

    if request.user.anime_des_seances:
        context['topic_ntfy_coach'] = request.user.topic_ntfy_coach

    return render(request, 'notifications/preferences.html', context)
