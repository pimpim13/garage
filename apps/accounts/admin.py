from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Famille, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = UserAdmin.list_display + ('role', 'famille')
    list_filter = UserAdmin.list_filter + ('role', 'famille')
    fieldsets = UserAdmin.fieldsets + (
        ('Salle de sport', {'fields': ('role', 'telephone', 'famille', 'tolerance_seances_negatives')}),
    )


@admin.register(Famille)
class FamilleAdmin(admin.ModelAdmin):
    list_display = ('nom', 'tolerance_seances_negatives')
    search_fields = ('nom',)
