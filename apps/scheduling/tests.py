import datetime

from django.test import TestCase
from django.utils import timezone

from .models import Seance


class PromotionListeAttentePossibleTests(TestCase):
    def test_vrai_si_la_seance_a_lieu_dans_plus_de_24h(self):
        seance = Seance(debut=timezone.now() + datetime.timedelta(hours=25))

        self.assertTrue(seance.promotion_liste_attente_possible)

    def test_faux_si_la_seance_a_lieu_dans_moins_de_24h(self):
        seance = Seance(debut=timezone.now() + datetime.timedelta(hours=23))

        self.assertFalse(seance.promotion_liste_attente_possible)
