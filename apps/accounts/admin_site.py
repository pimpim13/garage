from django.contrib.admin import AdminSite
from django.contrib.admin.apps import AdminConfig


class GarageAdminSite(AdminSite):
    def has_permission(self, request):
        return super().has_permission(request) and getattr(request.user, 'is_admin', False)


class GarageAdminConfig(AdminConfig):
    default_site = 'apps.accounts.admin_site.GarageAdminSite'
