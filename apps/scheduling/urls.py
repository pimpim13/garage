from django.urls import path

from . import views

app_name = 'scheduling'

urlpatterns = [
    path('', views.calendrier, name='calendrier'),
    path('semaine/<str:semaine>/', views.calendrier, name='calendrier_semaine'),
    path('seance/<int:pk>/', views.SeanceDetailView.as_view(), name='seance_detail'),
]
