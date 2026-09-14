from django.core.mail import send_mail
from django.utils import timezone

from apps.accounts.models import User


def notifier_ouverture_inscriptions_par_email(seance):
    debut = timezone.localtime(seance.debut)
    destinataires = User.objects.filter(
        role=User.Role.MEMBRE, is_active=True, accepte_emails=True
    ).exclude(email='')
    for membre in destinataires:
        send_mail(
            subject=f"Inscriptions ouvertes : {seance.nom} — Le Garage",
            message=(
                f"Bonjour {membre.get_full_name() or membre.username},\n\n"
                f"Les inscriptions sont ouvertes pour « {seance.nom} » le {debut:%d/%m à %H:%M}.\n\n"
                "L'équipe Le Garage"
            ),
            from_email=None,
            recipient_list=[membre.email],
        )
