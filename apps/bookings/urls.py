from django.urls import path

from . import views

app_name = 'bookings'

urlpatterns = [
    path('<int:seance_id>/inscrire/', views.inscrire, name='inscrire'),
    path('<int:seance_id>/desinscrire/', views.desinscrire, name='desinscrire'),
]
