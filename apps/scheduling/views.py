import datetime

from django.shortcuts import render
from django.utils import timezone
from django.views.generic import DetailView

from apps.bookings.models import Inscription

from .models import Seance


def _lundi(date):
    return date - datetime.timedelta(days=date.weekday())


def calendrier(request, semaine=None):
    aujourdhui = timezone.localdate()
    lundi = _lundi(datetime.date.fromisoformat(semaine)) if semaine else _lundi(aujourdhui)
    jours = [lundi + datetime.timedelta(days=i) for i in range(7)]

    jour_param = request.GET.get('jour')
    jour_selectionne = lundi
    if jour_param:
        try:
            candidat = datetime.date.fromisoformat(jour_param)
        except ValueError:
            candidat = None
        if candidat in jours:
            jour_selectionne = candidat
    elif aujourdhui in jours:
        jour_selectionne = aujourdhui

    seances_du_jour = (
        Seance.objects.filter(debut__date=jour_selectionne)
        .select_related('coach')
        .order_by('debut')
    )

    inscriptions_membre = set()
    if request.user.is_authenticated:
        inscriptions_membre = set(
            request.user.inscriptions.filter(
                statut=Inscription.Statut.INSCRIT, seance__in=seances_du_jour
            ).values_list('seance_id', flat=True)
        )

    context = {
        'lundi': lundi,
        'jours': jours,
        'jour_selectionne': jour_selectionne,
        'semaine_precedente': lundi - datetime.timedelta(days=7),
        'semaine_suivante': lundi + datetime.timedelta(days=7),
        'seances_du_jour': seances_du_jour,
        'inscriptions_membre': inscriptions_membre,
        'aujourdhui': aujourdhui,
    }
    return render(request, 'scheduling/calendrier.html', context)


class SeanceDetailView(DetailView):
    model = Seance
    template_name = 'scheduling/seance_detail.html'
    context_object_name = 'seance'

    def get_queryset(self):
        return super().get_queryset().select_related('coach')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['participants'] = self.object.inscriptions.filter(
            statut=Inscription.Statut.INSCRIT
        ).select_related('membre')
        if self.request.user.is_authenticated:
            context['inscrit'] = self.object.inscriptions.filter(
                membre=self.request.user, statut=Inscription.Statut.INSCRIT
            ).exists()
        return context
