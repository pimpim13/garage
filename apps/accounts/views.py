from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from .forms import MembreCreateForm, MembreUpdateForm
from .mixins import GestionnaireRequiredMixin
from .models import User


class HomeView(TemplateView):
    template_name = 'home.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('scheduling:calendrier')
        return super().get(request, *args, **kwargs)


class MembreListView(GestionnaireRequiredMixin, ListView):
    template_name = 'accounts/membre_liste.html'
    context_object_name = 'membres'

    def get_queryset(self):
        return User.objects.filter(role=User.Role.MEMBRE).order_by('first_name', 'username')


class MembreCreateView(GestionnaireRequiredMixin, CreateView):
    form_class = MembreCreateForm
    template_name = 'accounts/membre_form.html'
    success_url = reverse_lazy('accounts:membre_liste')

    def form_valid(self, form):
        messages.success(self.request, "Membre créé.")
        return super().form_valid(form)


class MembreUpdateView(GestionnaireRequiredMixin, UpdateView):
    form_class = MembreUpdateForm
    template_name = 'accounts/membre_form.html'
    success_url = reverse_lazy('accounts:membre_liste')

    def get_queryset(self):
        return User.objects.filter(role=User.Role.MEMBRE)

    def form_valid(self, form):
        messages.success(self.request, "Membre modifié.")
        return super().form_valid(form)


@login_required
@require_POST
def membre_toggle_actif(request, pk):
    if not request.user.is_staff_or_manager:
        raise PermissionDenied
    membre = get_object_or_404(User, pk=pk, role=User.Role.MEMBRE)
    membre.is_active = not membre.is_active
    membre.save(update_fields=['is_active'])
    if membre.is_active:
        messages.success(request, f"{membre} réactivé(e).")
    else:
        messages.success(request, f"{membre} désactivé(e).")
    return redirect('accounts:membre_liste')
