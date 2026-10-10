from django.urls import path

from . import views

app_name = 'statistiques'

urlpatterns = [
    path('', views.TableauDeBordView.as_view(), name='tableau_de_bord'),
]
