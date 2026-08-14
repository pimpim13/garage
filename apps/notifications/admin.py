from django.contrib import admin

from .models import PreferenceNotification


@admin.register(PreferenceNotification)
class PreferenceNotificationAdmin(admin.ModelAdmin):
    list_display = ('membre', 'type_evenement', 'canal', 'active')
    list_filter = ('type_evenement', 'canal', 'active')
