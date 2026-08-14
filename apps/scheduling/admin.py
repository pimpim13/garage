from django.contrib import admin

from .models import ModeleSeance, Seance


@admin.register(ModeleSeance)
class ModeleSeanceAdmin(admin.ModelAdmin):
    list_display = ('nom', 'duree_minutes', 'capacite_max_defaut', 'delai_annulation_defaut_heures')


@admin.register(Seance)
class SeanceAdmin(admin.ModelAdmin):
    list_display = ('nom', 'debut', 'coach', 'capacite_max', 'places_restantes')
    list_filter = ('coach', 'modele')
    date_hierarchy = 'debut'
