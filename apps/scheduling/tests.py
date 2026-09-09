import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.bookings.services import enregistrer_inscription
from apps.purchases.models import MouvementSeance

from .models import Seance

User = get_user_model()


class PromotionListeAttentePossibleTests(TestCase):
    def test_vrai_si_la_seance_a_lieu_dans_plus_de_24h(self):
        seance = Seance(debut=timezone.now() + datetime.timedelta(hours=25))

        self.assertTrue(seance.promotion_liste_attente_possible)

    def test_faux_si_la_seance_a_lieu_dans_moins_de_24h(self):
        seance = Seance(debut=timezone.now() + datetime.timedelta(hours=23))

        self.assertFalse(seance.promotion_liste_attente_possible)


class DesinscriptionTardiveTests(TestCase):
    def test_faux_si_la_seance_a_lieu_apres_le_delai_d_annulation(self):
        seance = Seance(debut=timezone.now() + datetime.timedelta(hours=25), delai_annulation_heures=24)

        self.assertFalse(seance.desinscription_tardive)

    def test_vrai_si_la_seance_a_lieu_dans_le_delai_d_annulation(self):
        seance = Seance(debut=timezone.now() + datetime.timedelta(hours=23), delai_annulation_heures=24)

        self.assertTrue(seance.desinscription_tardive)

    def test_vrai_si_la_seance_est_deja_passee(self):
        seance = Seance(debut=timezone.now() - datetime.timedelta(hours=1), delai_annulation_heures=24)

        self.assertTrue(seance.desinscription_tardive)


class SeanceDetailBoutonAbsenceTests(TestCase):
    def setUp(self):
        self.coach = User.objects.create_user(
            username='coach_fiche_seance', password='motdepasse123', role=User.Role.GESTIONNAIRE
        )
        self.membre = User.objects.create(username='membre_fiche_seance')
        MouvementSeance.objects.create(membre=self.membre, delta=5, motif=MouvementSeance.Motif.ACHAT)
        self.client.force_login(self.coach)

    def test_propose_non_presente_si_la_seance_est_passee(self):
        seance = Seance.objects.create(
            nom='WOD', debut=timezone.now() - datetime.timedelta(hours=1), coach=self.coach,
        )
        enregistrer_inscription(membre=self.membre, seance=seance, auteur=self.membre)

        response = self.client.get(reverse('scheduling:seance_detail', kwargs={'pk': seance.pk}))

        self.assertContains(response, 'Non présent(e)')
        self.assertNotContains(response, 'Désinscrire')

    def test_propose_desinscrire_si_la_seance_n_est_pas_encore_passee(self):
        seance = Seance.objects.create(
            nom='WOD', debut=timezone.now() + datetime.timedelta(days=2), coach=self.coach,
        )
        enregistrer_inscription(membre=self.membre, seance=seance, auteur=self.membre)

        response = self.client.get(reverse('scheduling:seance_detail', kwargs={'pk': seance.pk}))

        self.assertContains(response, 'Désinscrire')
        self.assertNotContains(response, 'Non présent(e)')
