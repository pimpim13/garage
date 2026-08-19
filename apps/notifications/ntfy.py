import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _envoyer(topic, message, titre):
    """Best-effort : ne lève jamais d'exception, n'interrompt jamais l'appelant."""
    if not topic:
        return
    try:
        requests.post(
            f"{settings.NTFY_BASE_URL}/{topic}",
            data=message.encode('utf-8'),
            headers={'Title': titre},
            timeout=5,
        )
    except requests.RequestException:
        logger.warning("Échec de l'envoi de la notification push ntfy.sh", exc_info=True)


def notifier_membres(message, titre="Le Garage"):
    """Canal membres : nouvelles séances, annulations."""
    _envoyer(settings.NTFY_TOPIC_MEMBRES, message, titre)


def notifier_coachs(message, titre="Le Garage"):
    """Canal coachs/gestionnaires : inscriptions, séances pleines."""
    _envoyer(settings.NTFY_TOPIC_COACHS, message, titre)
