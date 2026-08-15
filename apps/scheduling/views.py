import datetime
from collections import defaultdict
from types import SimpleNamespace

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.accounts.mixins import GestionnaireRequiredMixin
from apps.bookings.models import Inscription

from .forms import ModeleSeanceForm, SeanceForm
from .models import ModeleSeance, Seance


def _lundi(date):
    return date - datetime.timedelta(days=date.weekday())


def _calendrier_url_pour(debut):
    jour = timezone.localtime(debut).date()
    lundi = _lundi(jour)
    url = reverse('scheduling:calendrier_semaine', kwargs={'semaine': lundi.isoformat()})
    return f"{url}?jour={jour.isoformat()}"


def _modeles_data():
    return {
        str(modele.pk): {
            'nom': modele.nom,
            'duree_minutes': modele.duree_minutes,
            'capacite_max': modele.capacite_max_defaut,
            'delai_annulation_heures': modele.delai_annulation_defaut_heures,
        }
        for modele in ModeleSeance.objects.all()
    }


def _occupation_par_jour(jours):
    """Pour chaque jour, indique s'il y a des séances et si elles sont toutes complètes."""
    seances_semaine = Seance.objects.filter(debut__date__in=jours).annotate(
        nb_inscrits=Count('inscriptions', filter=Q(inscriptions__statut=Inscription.Statut.INSCRIT))
    )

    places_par_jour = defaultdict(list)
    for seance in seances_semaine:
        jour = timezone.localtime(seance.debut).date()
        places_par_jour[jour].append(seance.capacite_max - seance.nb_inscrits)

    statuts = {}
    for jour in jours:
        places = places_par_jour.get(jour)
        if not places:
            statuts[jour] = None
        elif any(p > 0 for p in places):
            statuts[jour] = 'vert'
        else:
            statuts[jour] = 'rouge'
    return statuts


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

    statuts_jours = _occupation_par_jour(jours)
    jours_info = [SimpleNamespace(date=jour, statut=statuts_jours[jour]) for jour in jours]

    context = {
        'lundi': lundi,
        'jours': jours_info,
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


class SeanceCreateView(GestionnaireRequiredMixin, CreateView):
    model = Seance
    form_class = SeanceForm
    template_name = 'scheduling/seance_form.html'

    def get_initial(self):
        initial = super().get_initial()
        jour = self.request.GET.get('jour')
        if jour:
            initial['debut'] = f"{jour}T09:00"
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['modeles_data'] = _modeles_data()
        return context

    def form_valid(self, form):
        messages.success(self.request, "Séance programmée.")
        return super().form_valid(form)

    def get_success_url(self):
        return _calendrier_url_pour(self.object.debut)


class SeanceUpdateView(GestionnaireRequiredMixin, UpdateView):
    model = Seance
    form_class = SeanceForm
    template_name = 'scheduling/seance_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['modeles_data'] = _modeles_data()
        return context

    def form_valid(self, form):
        messages.success(self.request, "Séance modifiée.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('scheduling:seance_detail', kwargs={'pk': self.object.pk})


class SeanceDeleteView(GestionnaireRequiredMixin, DeleteView):
    model = Seance
    template_name = 'scheduling/seance_confirm_delete.html'
    context_object_name = 'seance'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nb_participants'] = self.object.inscriptions.filter(
            statut=Inscription.Statut.INSCRIT
        ).count()
        return context

    def get_success_url(self):
        return _calendrier_url_pour(self.object.debut)

    def form_valid(self, form):
        messages.success(self.request, "Séance supprimée.")
        return super().form_valid(form)


class ModeleSeanceListView(GestionnaireRequiredMixin, ListView):
    model = ModeleSeance
    template_name = 'scheduling/modele_liste.html'
    context_object_name = 'modeles'


class ModeleSeanceCreateView(GestionnaireRequiredMixin, CreateView):
    model = ModeleSeance
    form_class = ModeleSeanceForm
    template_name = 'scheduling/modele_form.html'

    def get_success_url(self):
        return reverse('scheduling:modele_liste')

    def form_valid(self, form):
        messages.success(self.request, "Séance type créée.")
        return super().form_valid(form)
