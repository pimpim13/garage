from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.accounts.models import User


def notifier_ouverture_inscriptions_par_email(seance):
    debut = timezone.localtime(seance.debut)
    destinataires = User.objects.filter(
        role=User.Role.MEMBRE, is_active=True, email_ouverture_seance=True
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


def notifier_creation_compte_par_email(user, request):
    if not user.email:
        return
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    chemin = reverse('accounts:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
    protocole = 'https' if request.is_secure() else 'http'
    lien = f"{protocole}://{request.get_host()}{chemin}"
    send_mail(
        subject="Votre compte Le Garage — définissez votre mot de passe",
        message=(
            f"Bonjour {user.get_full_name() or user.username},\n\n"
            "Un compte a été créé pour vous sur Le Garage.\n\n"
            f"Identifiant de connexion : {user.username}\n\n"
            "Cliquez sur le lien ci-dessous pour définir votre mot de passe :\n"
            f"{lien}\n\n"
            "Si vous n'êtes pas à l'origine de cette demande, contactez votre coach.\n\n"
            "L'équipe Le Garage"
        ),
        from_email=None,
        recipient_list=[user.email],
    )
