from django.conf import settings
from django.db import models

from apps.scheduling.models import Seance


class Inscription(models.Model):
    class Statut(models.TextChoices):
        INSCRIT = 'inscrit', 'Inscrit'
        EN_ATTENTE = 'en_attente', "En liste d'attente"
        DESINSCRIT = 'desinscrit', 'Désinscrit'
        DESINSCRIT_TARDIF_JOKER = 'desinscrit_tardif_joker', 'Désinscrit tardivement (joker utilisé)'
        DESINSCRIT_TARDIF_SANS_JOKER = 'desinscrit_tardif_sans_joker', 'Désinscrit tardivement (séance perdue)'

    membre = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='inscriptions')
    seance = models.ForeignKey(Seance, on_delete=models.CASCADE, related_name='inscriptions')
    statut = models.CharField(max_length=40, choices=Statut.choices, default=Statut.INSCRIT)
    inscrit_le = models.DateTimeField(auto_now_add=True)
    desinscrit_le = models.DateTimeField(null=True, blank=True)
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='inscriptions_effectuees',
        help_text="Utilisateur à l'origine de l'action (le membre lui-même ou un gestionnaire/admin agissant pour lui).",
    )

    class Meta:
        ordering = ['-inscrit_le']
        constraints = [
            models.UniqueConstraint(
                fields=['membre', 'seance'],
                condition=models.Q(statut__in=['inscrit', 'en_attente']),
                name='unique_inscription_active_par_membre_et_seance',
            ),
        ]

    def __str__(self):
        return f"{self.membre} — {self.seance} ({self.get_statut_display()})"


class MouvementJoker(models.Model):
    class Motif(models.TextChoices):
        ATTRIBUTION = 'attribution', 'Attribution par un gestionnaire'
        UTILISATION = 'utilisation', "Utilisé lors d'une désinscription tardive"

    membre = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mouvements_jokers')
    delta = models.IntegerField(help_text="Positif pour une attribution, négatif pour une utilisation.")
    motif = models.CharField(max_length=20, choices=Motif.choices)
    inscription = models.ForeignKey(
        Inscription, on_delete=models.SET_NULL, null=True, blank=True, related_name='mouvements_jokers'
    )
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='jokers_attribues',
        help_text="Gestionnaire/admin à l'origine de l'attribution, ou le système lors d'une utilisation automatique.",
    )
    horodatage = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-horodatage']

    def __str__(self):
        return f"{self.membre} {self.delta:+d} ({self.get_motif_display()})"
