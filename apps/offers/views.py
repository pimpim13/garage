from django.views.generic import ListView

from .models import Offre


class CatalogueView(ListView):
    template_name = 'offers/catalogue.html'
    context_object_name = 'offres'

    def get_queryset(self):
        return Offre.objects.filter(active=True)
