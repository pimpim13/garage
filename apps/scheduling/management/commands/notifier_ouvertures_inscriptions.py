from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.email import notifier_ouverture_inscriptions_par_email
from apps.notifications.ntfy import notifier_membres
from apps.scheduling.models import Seance


class Command(BaseCommand):
    help = (
        "Notifie les membres pour les séances dont les inscriptions viennent de s'ouvrir "
        "(mercredi de la semaine précédant la séance, à 21h00). À exécuter via cron à 21h00, "
        "ou plus fréquemment pour réduire le délai de notification."
    )

    def handle(self, *args, **options):
        candidates = Seance.objects.filter(
            notification_ouverture_envoyee=False, debut__gte=timezone.now()
        )

        envoyees = 0
        for seance in candidates:
            if not seance.inscriptions_ouvertes:
                continue
            debut = timezone.localtime(seance.debut)
            notifier_membres(f"Inscriptions ouvertes : « {seance.nom} » le {debut:%d/%m à %H:%M}.")
            notifier_ouverture_inscriptions_par_email(seance)
            seance.notification_ouverture_envoyee = True
            seance.save(update_fields=['notification_ouverture_envoyee'])
            envoyees += 1

        self.stdout.write(self.style.SUCCESS(f"{envoyees} notification(s) d'ouverture envoyée(s)."))
