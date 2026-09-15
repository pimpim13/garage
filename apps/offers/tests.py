from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Offre


class SeedOffresCarnetTests(TestCase):
    def test_les_4_offres_carnet_existent(self):
        noms = set(Offre.objects.values_list('nom', flat=True))

        self.assertEqual(
            noms,
            {'1 séance', '10 séances + 1 offerte', '20 séances + 3 offertes', '25 séances + 5 offertes'},
        )

    def test_offre_a_l_unite_n_a_pas_de_duree_de_validite(self):
        offre = Offre.objects.get(nom='1 séance')

        self.assertEqual(offre.prix, Decimal('10'))
        self.assertEqual(offre.nombre_seances, 1)
        self.assertIsNone(offre.duree_validite_mois)

    def test_offre_10_plus_1_a_une_validite_de_3_mois(self):
        offre = Offre.objects.get(nom='10 séances + 1 offerte')

        self.assertEqual(offre.prix, Decimal('100'))
        self.assertEqual(offre.nombre_seances, 11)
        self.assertEqual(offre.duree_validite_mois, 3)

    def test_offre_20_plus_3_a_une_validite_de_6_mois(self):
        offre = Offre.objects.get(nom='20 séances + 3 offertes')

        self.assertEqual(offre.prix, Decimal('200'))
        self.assertEqual(offre.nombre_seances, 23)
        self.assertEqual(offre.duree_validite_mois, 6)

    def test_offre_25_plus_5_a_une_validite_de_6_mois(self):
        offre = Offre.objects.get(nom='25 séances + 5 offertes')

        self.assertEqual(offre.prix, Decimal('250'))
        self.assertEqual(offre.nombre_seances, 30)
        self.assertEqual(offre.duree_validite_mois, 6)

    def test_toutes_les_offres_sont_actives(self):
        self.assertFalse(Offre.objects.filter(active=False).exists())


class CatalogueViewTests(TestCase):
    def test_affiche_les_offres_actives(self):
        response = self.client.get(reverse('offers:catalogue'))

        self.assertContains(response, '1 séance')
        self.assertContains(response, '10 séances + 1 offerte')
        self.assertContains(response, '20 séances + 3 offertes')
        self.assertContains(response, '25 séances + 5 offertes')

    def test_n_affiche_pas_une_offre_inactive(self):
        Offre.objects.create(
            nom='Offre retirée', type_offre=Offre.TypeOffre.CARNET,
            prix=50, nombre_seances=5, active=False,
        )

        response = self.client.get(reverse('offers:catalogue'))

        self.assertNotContains(response, 'Offre retirée')

    def test_affiche_le_prix(self):
        response = self.client.get(reverse('offers:catalogue'))

        self.assertContains(response, '100')

    def test_ne_necessite_pas_d_etre_connecte(self):
        response = self.client.get(reverse('offers:catalogue'))

        self.assertEqual(response.status_code, 200)
