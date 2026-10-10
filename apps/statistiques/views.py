from django.utils import timezone
from django.views.generic import TemplateView

from apps.accounts.mixins import GestionnaireRequiredMixin
from apps.accounts.models import User

from . import services

PERIODES = [
    ('semaine', 'Semaine'),
    ('mois', 'Mois'),
    ('trimestre', 'Trimestre'),
    ('annee', 'Année'),
    ('perso', 'Personnalisée'),
]


class TableauDeBordView(GestionnaireRequiredMixin, TemplateView):
    template_name = 'statistiques/tableau_de_bord.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET
        periode = params.get('periode') if params.get('periode') in dict(PERIODES) else 'mois'
        debut, fin = services.resoudre_periode(
            periode, params.get('debut', ''), params.get('fin', ''), timezone.localdate()
        )
        coach_id = int(params['coach']) if params.get('coach', '').isdigit() else None
        nom = params.get('type', '')
        context.update(
            resultat=services.calculer(services.Filtres(debut=debut, fin=fin, nom=nom, coach_id=coach_id)),
            periodes=PERIODES,
            periode=periode,
            debut=debut,
            fin=fin,
            nom_selectionne=nom,
            coach_selectionne=coach_id,
            noms=services.noms_de_seances(),
            coachs=User.objects.filter(role__in=[User.Role.GESTIONNAIRE, User.Role.COACH, User.Role.ADMIN]),
        )
        return context
