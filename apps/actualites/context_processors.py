from .models import Actualite


def actualites_navbar(request):
    if not request.user.is_authenticated:
        return {}
    return {'actualites_navbar': list(Actualite.objects.actives()[:3])}
