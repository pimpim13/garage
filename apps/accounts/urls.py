from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('connexion/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('deconnexion/', auth_views.LogoutView.as_view(), name='logout'),
    path('membres/', views.MembreListView.as_view(), name='membre_liste'),
    path('membres/nouveau/', views.MembreCreateView.as_view(), name='membre_creer'),
    path('membres/<int:pk>/toggle-actif/', views.membre_toggle_actif, name='membre_toggle_actif'),
]
