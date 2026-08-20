from django.urls import path

from . import views

app_name = 'scheduling'

urlpatterns = [
    path('', views.calendrier, name='calendrier'),
    path('semaine/<str:semaine>/', views.calendrier, name='calendrier_semaine'),
    path('mois/', views.calendrier_mois, name='calendrier_mois'),
    path('mois/<str:mois>/', views.calendrier_mois, name='calendrier_mois_precis'),
    path('seance/<int:pk>/', views.SeanceDetailView.as_view(), name='seance_detail'),
    path('seance/<int:pk>/modifier/', views.SeanceUpdateView.as_view(), name='seance_modifier'),
    path('seance/<int:pk>/supprimer/', views.SeanceDeleteView.as_view(), name='seance_supprimer'),
    path('nouvelle-seance/', views.SeanceCreateView.as_view(), name='seance_creer'),
    path('modeles/', views.ModeleSeanceListView.as_view(), name='modele_liste'),
    path('modeles/nouveau/', views.ModeleSeanceCreateView.as_view(), name='modele_creer'),
    path('modeles/<int:pk>/modifier/', views.ModeleSeanceUpdateView.as_view(), name='modele_modifier'),
    path('modeles/<int:pk>/supprimer/', views.ModeleSeanceDeleteView.as_view(), name='modele_supprimer'),
]
