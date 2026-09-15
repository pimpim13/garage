from django.urls import path

from . import views

app_name = 'offers'

urlpatterns = [
    path('', views.CatalogueView.as_view(), name='catalogue'),
]
