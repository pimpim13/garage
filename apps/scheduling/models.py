import datetime

from django.conf import settings
from django.db import models
from django.utils import timezone


class ModeleSeance(models.Model):
    nom = models.CharField(max_length=100)
    duree_minutes = models.PositiveIntegerField(default=60)
    capacite_max_defaut = models.PositiveIntegerField()
    delai_annulation_defaut_heures = models.PositiveIntegerField(
        default=24,
        help_text="Délai avant le début de la séance en dessous duquel une désinscription est considérée tardive.",
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Seance(models.Model):
    modele = models.ForeignKey(
        ModeleSeance, on_delete=models.SET_NULL, null=True, blank=True, related_name='seances'
    )
    nom = models.CharField(max_length=100)
    debut = models.DateTimeField()
    duree_minutes = models.PositiveIntegerField(default=60)
    capacite_max = models.PositiveIntegerField(default=12)
    delai_annulation_heures = models.PositiveIntegerField(default=24)
    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='seances_animees'
    )
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['debut']

    def __str__(self):
        return f"{self.nom} — {self.debut:%d/%m/%Y %H:%M}"

    @property
    def fin(self):
        return self.debut + datetime.timedelta(minutes=self.duree_minutes)

    @property
    def est_passee(self):
        return self.debut < timezone.now()

    @property
    def places_restantes(self):
        from apps.bookings.models import Inscription

        return self.capacite_max - self.inscriptions.filter(statut=Inscription.Statut.INSCRIT).count()
