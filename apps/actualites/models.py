from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

MAX_ACTUALITES_CONCURRENTES = 3


class ActualiteQuerySet(models.QuerySet):
    def actives(self):
        aujourd_hui = timezone.localdate()
        return self.filter(date_debut__lte=aujourd_hui, date_fin__gte=aujourd_hui)


class Actualite(models.Model):
    texte = models.CharField(max_length=200)
    date_debut = models.DateField()
    date_fin = models.DateField()

    objects = ActualiteQuerySet.as_manager()

    class Meta:
        ordering = ['date_debut']

    def __str__(self):
        return self.texte

    def clean(self):
        super().clean()
        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError({'date_fin': "La date de fin doit être postérieure à la date de début."})
        if self.date_debut and self.date_fin:
            chevauchantes = Actualite.objects.filter(
                date_debut__lte=self.date_fin, date_fin__gte=self.date_debut
            ).exclude(pk=self.pk)
            if chevauchantes.count() >= MAX_ACTUALITES_CONCURRENTES:
                raise ValidationError(
                    f"Il y a déjà {MAX_ACTUALITES_CONCURRENTES} actualités programmées sur cette période. "
                    "Supprimez-en une ou modifiez les dates avant d'en ajouter une nouvelle."
                )
