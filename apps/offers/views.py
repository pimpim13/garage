from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.accounts.mixins import GestionnaireRequiredMixin

from .forms import OffreForm
from .models import Offre


class CatalogueView(ListView):
    template_name = 'offers/catalogue.html'
    context_object_name = 'offres'

    def get_queryset(self):
        if self.request.user.is_authenticated and self.request.user.is_staff_or_manager:
            return Offre.objects.all()
        return Offre.objects.filter(active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['peut_gerer'] = self.request.user.is_authenticated and self.request.user.is_staff_or_manager
        return context


class OffreCreateView(GestionnaireRequiredMixin, CreateView):
    model = Offre
    form_class = OffreForm
    template_name = 'offers/offre_form.html'
    success_url = reverse_lazy('offers:catalogue')

    def form_valid(self, form):
        messages.success(self.request, "Offre créée.")
        return super().form_valid(form)


class OffreUpdateView(GestionnaireRequiredMixin, UpdateView):
    model = Offre
    form_class = OffreForm
    template_name = 'offers/offre_form.html'
    success_url = reverse_lazy('offers:catalogue')

    def form_valid(self, form):
        messages.success(self.request, "Offre modifiée.")
        return super().form_valid(form)


class OffreDeleteView(GestionnaireRequiredMixin, DeleteView):
    model = Offre
    template_name = 'offers/offre_confirm_delete.html'
    success_url = reverse_lazy('offers:catalogue')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nb_achats'] = self.object.achats.count()
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                f"Impossible de supprimer « {self.object.nom} » : des achats y sont rattachés. "
                "Désactive-la plutôt pour qu'elle disparaisse du catalogue public.",
            )
            return redirect('offers:catalogue')
        messages.success(self.request, "Offre supprimée.")
        return response


@login_required
@require_POST
def offre_toggle_actif(request, pk):
    if not request.user.is_staff_or_manager:
        raise PermissionDenied
    offre = get_object_or_404(Offre, pk=pk)
    offre.active = not offre.active
    offre.save(update_fields=['active'])
    if offre.active:
        messages.success(request, f"« {offre.nom} » réactivée.")
    else:
        messages.success(request, f"« {offre.nom} » désactivée.")
    return redirect('offers:catalogue')
