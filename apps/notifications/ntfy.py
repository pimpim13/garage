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


def notifier_coach(coach, message, titre="Le Garage"):
    """Canal individuel d'un coach : sa séance est pleine, désinscription dans une de ses séances."""
    if coach is None:
        return
    _envoyer(coach.topic_ntfy_coach, message, titre)


def notifier_evenement_seance(seance, message, champ_preference, titre="Le Garage"):
    """Notifie individuellement chaque compte concerné par un événement de séance, selon ses préférences.

    - Le coach animant la séance est notifié s'il a activé `champ_preference`.
    - Un coach gestionnaire/admin est notifié s'il a activé `champ_preference` et qu'il suit ce coach
      (`coachs_suivis` vide = il suit tout le monde).
    """
    from apps.accounts.models import User

    destinataires = {}
    if seance.coach and getattr(seance.coach, champ_preference):
        destinataires[seance.coach.pk] = seance.coach

    gestionnaires = User.objects.filter(role__in=[User.Role.ADMIN, User.Role.GESTIONNAIRE])
    for gestionnaire in gestionnaires:
        if gestionnaire.pk in destinataires or not getattr(gestionnaire, champ_preference):
            continue
        suivis = gestionnaire.coachs_suivis.all()
        if not suivis.exists() or (seance.coach and suivis.filter(pk=seance.coach.pk).exists()):
            destinataires[gestionnaire.pk] = gestionnaire

    for destinataire in destinataires.values():
        notifier_coach(destinataire, message, titre)
