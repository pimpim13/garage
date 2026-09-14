from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


@login_required
def preferences(request):
    context = {}

    if request.user.is_membre:
        if request.method == 'POST':
            request.user.accepte_emails = 'accepte_emails' in request.POST
            request.user.save(update_fields=['accepte_emails'])
            messages.success(request, "Préférences de notification mises à jour.")
            return redirect('notifications:preferences')
        context['accepte_emails'] = request.user.accepte_emails
        context['topic_ntfy_membres'] = settings.NTFY_TOPIC_MEMBRES

    if request.user.anime_des_seances:
        context['topic_ntfy_coach'] = request.user.topic_ntfy_coach

    return render(request, 'notifications/preferences.html', context)
