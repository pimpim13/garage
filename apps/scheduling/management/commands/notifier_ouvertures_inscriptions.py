from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.ntfy import notifier_membres
from apps.scheduling.models import Seance


class Command(BaseCommand):
    help = (
        "Notifie les membres pour les séances dont les inscriptions viennent de s'ouvrir "
        "(mercredi de la semaine précédant la séance). À exécuter une fois par jour (cron)."
    )

    def handle(self, *args, **options):
        aujourdhui = timezone.localdate()
        candidates = Seance.objects.filter(
            notification_ouverture_envoyee=False, debut__gte=timezone.now()
        )

        envoyees = 0
        for seance in candidates:
            if seance.date_ouverture_inscriptions > aujourdhui:
                continue
            debut = timezone.localtime(seance.debut)
            notifier_membres(f"Inscriptions ouvertes : « {seance.nom} » le {debut:%d/%m à %H:%M}.")
            seance.notification_ouverture_envoyee = True
            seance.save(update_fields=['notification_ouverture_envoyee'])
            envoyees += 1

        self.stdout.write(self.style.SUCCESS(f"{envoyees} notification(s) d'ouverture envoyée(s)."))
