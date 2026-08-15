from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class GestionnaireRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Réserve une vue aux utilisateurs Gestionnaire ou Admin."""

    def test_func(self):
        return self.request.user.is_staff_or_manager
