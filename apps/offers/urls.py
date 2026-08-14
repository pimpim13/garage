from django.urls import path
from django.views.generic import TemplateView

app_name = 'offers'

urlpatterns = [
    path('', TemplateView.as_view(template_name='offers/catalogue.html'), name='catalogue'),
]
