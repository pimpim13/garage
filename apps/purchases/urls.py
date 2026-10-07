from django.urls import path

from . import views

app_name = 'purchases'

urlpatterns = [
    path('mon-solde/', views.mon_solde, name='mon_solde'),
    path('mon-solde/export/', views.export_mon_solde, name='export_mon_solde'),
    path('historique/<int:membre_id>/', views.historique_membre, name='historique_membre'),
    path('historique/<int:membre_id>/export/', views.export_historique_membre, name='export_historique_membre'),
    path('ajuster/<int:membre_id>/', views.ajuster_solde_membre, name='ajuster_solde'),
    path('achat/<int:membre_id>/', views.enregistrer_achat_membre, name='enregistrer_achat'),
]
