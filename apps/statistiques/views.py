import datetime
from urllib.parse import urlencode

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
        aujourd_hui = timezone.localdate()
        try:
            reference = datetime.date.fromisoformat(params.get('ref', ''))
        except ValueError:
            reference = aujourd_hui
        debut, fin = services.resoudre_periode(periode, params.get('debut', ''), params.get('fin', ''), reference)
        coach_id = int(params['coach']) if params.get('coach', '').isdigit() else None
        nom = params.get('type', '')
        url_precedent = self._url_voisine(periode, debut, fin, -1, nom, coach_id)
        url_suivant = None
        if fin < aujourd_hui:
            url_suivant = self._url_voisine(periode, debut, fin, 1, nom, coach_id)
        context.update(
            resultat=services.calculer(services.Filtres(debut=debut, fin=fin, nom=nom, coach_id=coach_id)),
            periodes=PERIODES,
            periode=periode,
            url_precedent=url_precedent,
            url_suivant=url_suivant,
            debut=debut,
            fin=fin,
            nom_selectionne=nom,
            coach_selectionne=coach_id,
            noms=services.noms_de_seances(),
            coachs=User.objects.filter(role__in=[User.Role.GESTIONNAIRE, User.Role.COACH, User.Role.ADMIN]),
        )
        return context

    @staticmethod
    def _url_voisine(periode, debut, fin, sens, nom, coach_id):
        nouveau_debut, nouvelle_fin = services.periode_voisine(periode, debut, fin, sens)
        params = {'periode': periode}
        if periode == 'perso':
            params.update(debut=nouveau_debut.isoformat(), fin=nouvelle_fin.isoformat())
        else:
            params['ref'] = nouveau_debut.isoformat() if sens > 0 else nouvelle_fin.isoformat()
        if nom:
            params['type'] = nom
        if coach_id:
            params['coach'] = coach_id
        return '?' + urlencode(params)
