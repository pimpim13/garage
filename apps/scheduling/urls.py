from django.urls import path

from . import views

app_name = 'scheduling'

urlpatterns = [
    path('', views.calendrier, name='calendrier'),
    path('semaine/<str:semaine>/', views.calendrier, name='calendrier_semaine'),
    path('seance/<int:pk>/', views.SeanceDetailView.as_view(), name='seance_detail'),
    path('nouvelle-seance/', views.SeanceCreateView.as_view(), name='seance_creer'),
    path('modeles/', views.ModeleSeanceListView.as_view(), name='modele_liste'),
    path('modeles/nouveau/', views.ModeleSeanceCreateView.as_view(), name='modele_creer'),
]
