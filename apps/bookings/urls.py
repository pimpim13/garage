from django.urls import path

from . import views

app_name = 'bookings'

urlpatterns = [
    path('<int:seance_id>/inscrire/', views.inscrire, name='inscrire'),
    path('<int:seance_id>/desinscrire/', views.desinscrire, name='desinscrire'),
    path('<int:seance_id>/liste-attente/rejoindre/', views.liste_attente_rejoindre, name='liste_attente_rejoindre'),
    path('<int:seance_id>/liste-attente/quitter/', views.liste_attente_quitter, name='liste_attente_quitter'),
    path('<int:seance_id>/inscrire-membre/', views.inscrire_membre, name='inscrire_membre'),
    path('<int:seance_id>/desinscrire-membre/<int:membre_id>/', views.desinscrire_membre, name='desinscrire_membre'),
]
