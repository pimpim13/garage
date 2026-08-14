from django.urls import path
from django.views.generic import TemplateView

app_name = 'scheduling'

urlpatterns = [
    path('', TemplateView.as_view(template_name='scheduling/calendrier.html'), name='calendrier'),
]
