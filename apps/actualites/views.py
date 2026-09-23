from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.accounts.mixins import GestionnaireRequiredMixin

from .forms import ActualiteForm
from .models import Actualite


class ActualiteListView(GestionnaireRequiredMixin, ListView):
    model = Actualite
    template_name = 'actualites/actualite_liste.html'
    context_object_name = 'actualites'


class ActualiteCreateView(GestionnaireRequiredMixin, CreateView):
    model = Actualite
    form_class = ActualiteForm
    template_name = 'actualites/actualite_form.html'
    success_url = reverse_lazy('actualites:liste')

    def form_valid(self, form):
        messages.success(self.request, "Actualité créée.")
        return super().form_valid(form)


class ActualiteUpdateView(GestionnaireRequiredMixin, UpdateView):
    model = Actualite
    form_class = ActualiteForm
    template_name = 'actualites/actualite_form.html'
    success_url = reverse_lazy('actualites:liste')

    def form_valid(self, form):
        messages.success(self.request, "Actualité modifiée.")
        return super().form_valid(form)


class ActualiteDeleteView(GestionnaireRequiredMixin, DeleteView):
    model = Actualite
    template_name = 'actualites/actualite_confirm_delete.html'
    success_url = reverse_lazy('actualites:liste')

    def form_valid(self, form):
        messages.success(self.request, "Actualité supprimée.")
        return super().form_valid(form)
