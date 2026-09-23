from django.urls import path

from . import views

app_name = 'actualites'

urlpatterns = [
    path('', views.ActualiteListView.as_view(), name='liste'),
    path('nouvelle/', views.ActualiteCreateView.as_view(), name='creer'),
    path('<int:pk>/modifier/', views.ActualiteUpdateView.as_view(), name='modifier'),
    path('<int:pk>/supprimer/', views.ActualiteDeleteView.as_view(), name='supprimer'),
]
