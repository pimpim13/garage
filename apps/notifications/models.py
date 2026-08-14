from django.conf import settings
from django.db import models


class TypeEvenement(models.TextChoices):
    INSCRIPTION = 'inscription', 'Inscription à une séance'
    DESINSCRIPTION = 'desinscription', 'Désinscription'
    JOKER_UTILISE = 'joker_utilise', 'Joker utilisé'
    NOUVELLE_SEANCE = 'nouvelle_seance', "Ouverture d'une nouvelle séance"
    SOLDE_FAIBLE = 'solde_faible', 'Nombre de séances restantes faible'


class PreferenceNotification(models.Model):
    class Canal(models.TextChoices):
        EMAIL = 'email', 'Email'

    membre = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='preferences_notifications'
    )
    type_evenement = models.CharField(max_length=30, choices=TypeEvenement.choices)
    canal = models.CharField(max_length=20, choices=Canal.choices, default=Canal.EMAIL)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['membre', 'type_evenement', 'canal'],
                name='unique_preference_par_membre_evenement_canal',
            ),
        ]

    def __str__(self):
        return f"{self.membre} — {self.get_type_evenement_display()} ({self.get_canal_display()})"
