from django.urls import path

from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.preferences, name='preferences'),
    path('tester/', views.tester_notification, name='tester_notification'),
]
