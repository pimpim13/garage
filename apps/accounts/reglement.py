"""Règlement intérieur du Garage : version courante et garde-fou d'acceptation.

Pour publier une nouvelle version du texte (templates/accounts/_reglement_texte.html), il suffit
de changer VERSION : tous les membres devront ré-accepter à leur prochaine inscription.
"""
from functools import wraps

from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

VERSION = '2026-11-10'


def reglement_requis(vue):
    """Redirige vers la page d'acceptation si l'utilisateur n'a pas accepté la version courante.

    À placer sous @login_required. Le retour se fait sur la page d'où vient la requête (`next`
    ou Referer), jamais sur l'URL d'action qui n'accepte que POST.
    """

    @wraps(vue)
    def enveloppe(request, *args, **kwargs):
        if not request.user.reglement_a_jour:
            retour = request.POST.get('next') or request.META.get('HTTP_REFERER') or ''
            if not url_has_allowed_host_and_scheme(
                retour, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                retour = ''
            url = reverse('accounts:reglement_accepter')
            return redirect(f"{url}?next={retour}" if retour else url)
        return vue(request, *args, **kwargs)

    return enveloppe
