from django.db import models


class Offre(models.Model):
    class TypeOffre(models.TextChoices):
        CARNET = 'carnet', 'Carnet de séances'
        FAMILLE = 'famille', 'Offre famille'
        PERSONNALISEE = 'personnalisee', 'Offre personnalisée'

    nom = models.CharField(max_length=100)
    type_offre = models.CharField(max_length=20, choices=TypeOffre.choices)
    description = models.TextField(blank=True)
    prix = models.DecimalField(max_digits=8, decimal_places=2)
    nombre_seances = models.PositiveIntegerField()
    duree_validite_mois = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Durée (en mois) dont un achat de cette offre prolonge la validité de l'ensemble du solde "
        "du membre (ou de sa famille). Vide = n'affecte pas la date d'expiration (ex : achat à l'unité).",
    )
    active = models.BooleanField(default=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nom']

    def __str__(self):
        return f"{self.nom} ({self.get_type_offre_display()})"
