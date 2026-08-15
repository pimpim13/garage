from django.contrib.auth.models import AbstractUser
from django.db import models


class Famille(models.Model):
    nom = models.CharField(max_length=100)
    tolerance_seances_negatives = models.PositiveIntegerField(
        default=0,
        help_text="Tolérance de séances négatives appliquée au pool partagé, pour tous les membres liés.",
    )
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'famille'
        verbose_name_plural = 'familles'
        ordering = ['nom']

    def __str__(self):
        return self.nom


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrateur'
        GESTIONNAIRE = 'gestionnaire', 'Gestionnaire'
        MEMBRE = 'membre', 'Membre'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBRE)
    telephone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='téléphone',
        help_text="Utilisé pour les notifications par SMS/WhatsApp (à venir).",
    )
    famille = models.ForeignKey(
        Famille,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='membres',
        help_text="Si renseigné, ce membre partage le pool de séances et la tolérance négative de sa famille.",
    )
    tolerance_seances_negatives = models.PositiveIntegerField(
        default=0,
        verbose_name='tolérance de séances négatives',
        help_text="Nombre de séances que ce membre peut avoir en négatif avant blocage de l'inscription. "
        "Ignoré si le membre appartient à une famille (voir Famille.tolerance_seances_negatives).",
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

    @property
    def tolerance_applicable(self):
        return self.famille.tolerance_seances_negatives if self.famille_id else self.tolerance_seances_negatives

    def __str__(self):
        return self.get_full_name() or self.username
