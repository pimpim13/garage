from django.urls import path

from . import views

app_name = 'bookings'

urlpatterns = [
    path('<int:seance_id>/inscrire/', views.inscrire, name='inscrire'),
    path('<int:seance_id>/desinscrire/', views.desinscrire, name='desinscrire'),
    path('<int:seance_id>/liste-attente/rejoindre/', views.liste_attente_rejoindre, name='liste_attente_rejoindre'),
    path('<int:seance_id>/liste-attente/quitter/', views.liste_attente_quitter, name='liste_attente_quitter'),
]
