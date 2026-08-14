from django.contrib import admin

from .models import Offre


@admin.register(Offre)
class OffreAdmin(admin.ModelAdmin):
    list_display = ('nom', 'type_offre', 'prix', 'nombre_seances', 'active')
    list_filter = ('type_offre', 'active')
    search_fields = ('nom',)
