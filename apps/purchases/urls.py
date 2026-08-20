from django.urls import path

from . import views

app_name = 'purchases'

urlpatterns = [
    path('mon-solde/', views.mon_solde, name='mon_solde'),
    path('ajuster/<int:membre_id>/', views.ajuster_solde_membre, name='ajuster_solde'),
]
