from django.contrib import admin

from .models import Achat, MouvementSeance


@admin.register(Achat)
class AchatAdmin(admin.ModelAdmin):
    list_display = ('membre', 'offre', 'date_achat', 'nombre_seances', 'prix_paye', 'statut_paiement')
    list_filter = ('statut_paiement', 'offre')
    search_fields = ('membre__username', 'membre__first_name', 'membre__last_name')


@admin.register(MouvementSeance)
class MouvementSeanceAdmin(admin.ModelAdmin):
    list_display = ('membre', 'delta', 'motif', 'horodatage', 'auteur')
    list_filter = ('motif',)
