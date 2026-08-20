from django.contrib import admin
from django.urls import include, path

from apps.accounts.views import HomeView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', HomeView.as_view(), name='home'),
    path('comptes/', include('apps.accounts.urls')),
    path('calendrier/', include('apps.scheduling.urls')),
    path('reservations/', include('apps.bookings.urls')),
    path('offres/', include('apps.offers.urls')),
    path('solde/', include('apps.purchases.urls')),
]
