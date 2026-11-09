from django.shortcuts import resolve_url
from django.utils.http import url_has_allowed_host_and_scheme


def url_suivante(request, defaut):
    """Renvoie l'URL « next » du formulaire si elle reste sur ce site, sinon `defaut`.

    Évite une redirection ouverte vers un site externe (ex. next=https://site-piege.example).
    `defaut` peut être un nom d'URL ('accounts:membre_liste') ou un chemin.
    """
    suivante = request.POST.get('next')
    if suivante and url_has_allowed_host_and_scheme(
        suivante, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return suivante
    return resolve_url(defaut)
