from django.urls import path

from . import views

app_name = 'offers'

urlpatterns = [
    path('', views.CatalogueView.as_view(), name='catalogue'),
    path('nouveau/', views.OffreCreateView.as_view(), name='offre_creer'),
    path('<int:pk>/modifier/', views.OffreUpdateView.as_view(), name='offre_modifier'),
    path('<int:pk>/supprimer/', views.OffreDeleteView.as_view(), name='offre_supprimer'),
    path('<int:pk>/toggle-actif/', views.offre_toggle_actif, name='offre_toggle_actif'),
]
