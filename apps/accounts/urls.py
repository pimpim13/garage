from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = 'accounts'

urlpatterns = [
    path('connexion/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('deconnexion/', auth_views.LogoutView.as_view(), name='logout'),
    path(
        'mot-de-passe/',
        auth_views.PasswordChangeView.as_view(
            template_name='accounts/password_change_form.html',
            success_url=reverse_lazy('accounts:password_change_done'),
        ),
        name='password_change',
    ),
    path(
        'mot-de-passe/termine/',
        auth_views.PasswordChangeDoneView.as_view(template_name='accounts/password_change_done.html'),
        name='password_change_done',
    ),
    path('membres/', views.MembreListView.as_view(), name='membre_liste'),
    path('membres/nouveau/', views.MembreCreateView.as_view(), name='membre_creer'),
    path('membres/<int:pk>/modifier/', views.MembreUpdateView.as_view(), name='membre_modifier'),
    path('membres/<int:pk>/toggle-actif/', views.membre_toggle_actif, name='membre_toggle_actif'),
]
