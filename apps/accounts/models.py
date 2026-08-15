from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrateur'
        GESTIONNAIRE = 'gestionnaire', 'Gestionnaire'
        MEMBRE = 'membre', 'Membre'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBRE)
    telephone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Utilisé pour les notifications par SMS/WhatsApp (à venir).",
    )
    tolerance_seances_negatives = models.PositiveIntegerField(
        default=0,
        help_text="Nombre de séances que ce membre peut avoir en négatif avant blocage de l'inscription.",
    )

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_gestionnaire(self):
        return self.role == self.Role.GESTIONNAIRE

    @property
    def is_membre(self):
        return self.role == self.Role.MEMBRE

    @property
    def is_staff_or_manager(self):
        return self.role in (self.Role.ADMIN, self.Role.GESTIONNAIRE)

    def __str__(self):
        return self.get_full_name() or self.username
