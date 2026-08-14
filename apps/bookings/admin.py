from django.contrib import admin

from .models import Inscription, MouvementJoker


@admin.register(Inscription)
class InscriptionAdmin(admin.ModelAdmin):
    list_display = ('membre', 'seance', 'statut', 'inscrit_le', 'desinscrit_le')
    list_filter = ('statut',)
    search_fields = ('membre__username', 'membre__first_name', 'membre__last_name')


@admin.register(MouvementJoker)
class MouvementJokerAdmin(admin.ModelAdmin):
    list_display = ('membre', 'delta', 'motif', 'horodatage', 'auteur')
    list_filter = ('motif',)
