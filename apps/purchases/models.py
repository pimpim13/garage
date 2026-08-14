from django.conf import settings
from django.db import models

from apps.offers.models import Offre


class Achat(models.Model):
    class StatutPaiement(models.TextChoices):
        EN_ATTENTE = 'en_attente', 'En attente'
        PAYE = 'paye', 'Payé'
        ANNULE = 'annule', 'Annulé'

    membre = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='achats')
    offre = models.ForeignKey(Offre, on_delete=models.PROTECT, related_name='achats')
    date_achat = models.DateTimeField(auto_now_add=True)
    nombre_seances = models.PositiveIntegerField(
        help_text="Nombre de séances accordées par cet achat (copié depuis l'offre au moment de l'achat)."
    )
    prix_paye = models.DecimalField(max_digits=8, decimal_places=2)
    statut_paiement = models.CharField(
        max_length=20, choices=StatutPaiement.choices, default=StatutPaiement.EN_ATTENTE
    )
    saisi_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='achats_saisis',
        help_text="Gestionnaire ou admin ayant enregistré cet achat.",
    )

    class Meta:
        ordering = ['-date_achat']

    def __str__(self):
        return f"{self.offre.nom} — {self.membre} ({self.date_achat:%d/%m/%Y})"


class MouvementSeance(models.Model):
    class Motif(models.TextChoices):
        ACHAT = 'achat', 'Achat de carnet'
        INSCRIPTION = 'inscription', 'Inscription à une séance'
        DESINSCRIPTION = 'desinscription', 'Désinscription'
        DESINSCRIPTION_TARDIVE_JOKER = 'desinscription_tardive_joker', 'Désinscription tardive (joker utilisé)'
        AJUSTEMENT = 'ajustement', 'Ajustement manuel'

    membre = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mouvements_seances')
    delta = models.IntegerField(help_text="Positif pour un crédit, négatif pour un débit.")
    motif = models.CharField(max_length=40, choices=Motif.choices)
    achat = models.ForeignKey(
        Achat, on_delete=models.SET_NULL, null=True, blank=True, related_name='mouvements'
    )
    inscription = models.ForeignKey(
        'bookings.Inscription', on_delete=models.SET_NULL, null=True, blank=True, related_name='mouvements_seances'
    )
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='mouvements_effectues',
        help_text="Utilisateur à l'origine de l'action (le membre lui-même ou un gestionnaire/admin).",
    )
    horodatage = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-horodatage']

    def __str__(self):
        return f"{self.membre} {self.delta:+d} ({self.get_motif_display()})"
