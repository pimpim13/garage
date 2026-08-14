from django.shortcuts import redirect
from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = 'home.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_staff_or_manager:
                return redirect('admin:index')
            return redirect('scheduling:calendrier')
        return super().get(request, *args, **kwargs)
