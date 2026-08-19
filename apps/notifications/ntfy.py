import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def envoyer_push(message, titre="Le Garage", topic=None):
    """Envoie une notification push via ntfy.sh. Best-effort : ne lève jamais d'exception."""
    topic = topic or settings.NTFY_TOPIC
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
