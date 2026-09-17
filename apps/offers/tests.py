from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Offre

User = get_user_model()


def creer_gestionnaire(**kwargs):
    kwargs.setdefault('username', 'gestionnaire_offres')
    kwargs.setdefault('role', User.Role.GESTIONNAIRE)
    return User.objects.create_user(password='motdepasse123', **kwargs)


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

    def test_un_gestionnaire_voit_aussi_les_offres_inactives(self):
        Offre.objects.create(
            nom='Offre retirée visible gestionnaire', type_offre=Offre.TypeOffre.CARNET,
            prix=50, nombre_seances=5, active=False,
        )
        gestionnaire = creer_gestionnaire()
        self.client.force_login(gestionnaire)

        response = self.client.get(reverse('offers:catalogue'))

        self.assertContains(response, 'Offre retirée visible gestionnaire')

    def test_un_gestionnaire_voit_les_boutons_de_gestion(self):
        gestionnaire = creer_gestionnaire(username='gestionnaire_boutons')
        self.client.force_login(gestionnaire)

        response = self.client.get(reverse('offers:catalogue'))

        self.assertContains(response, 'Nouvelle offre')
        self.assertContains(response, 'Modifier')
        self.assertContains(response, 'Supprimer')

    def test_un_membre_ne_voit_pas_les_boutons_de_gestion(self):
        membre = User.objects.create_user(username='membre_sans_gestion_offre', password='motdepasse123')
        self.client.force_login(membre)

        response = self.client.get(reverse('offers:catalogue'))

        self.assertNotContains(response, 'Nouvelle offre')


class OffreCreateViewTests(TestCase):
    def setUp(self):
        self.gestionnaire = creer_gestionnaire(username='gestionnaire_creer_offre')
        self.client.force_login(self.gestionnaire)

    def test_propose_un_bouton_annuler_vers_le_catalogue(self):
        response = self.client.get(reverse('offers:offre_creer'))

        self.assertContains(response, 'Annuler')
        self.assertContains(response, reverse('offers:catalogue'))

    def test_un_membre_ne_peut_pas_creer_d_offre(self):
        membre = User.objects.create_user(username='membre_creer_offre', password='motdepasse123')
        self.client.force_login(membre)

        response = self.client.get(reverse('offers:offre_creer'))

        self.assertEqual(response.status_code, 403)

    def test_cree_une_offre(self):
        response = self.client.post(reverse('offers:offre_creer'), {
            'nom': 'Offre test création',
            'type_offre': Offre.TypeOffre.CARNET,
            'description': '',
            'prix': '150',
            'nombre_seances': 15,
            'duree_validite_mois': 4,
            'active': 'on',
        })

        self.assertRedirects(response, reverse('offers:catalogue'))
        offre = Offre.objects.get(nom='Offre test création')
        self.assertEqual(offre.duree_validite_mois, 4)

    def test_duree_de_validite_facultative(self):
        response = self.client.post(reverse('offers:offre_creer'), {
            'nom': 'Offre sans validité',
            'type_offre': Offre.TypeOffre.CARNET,
            'description': '',
            'prix': '15',
            'nombre_seances': 1,
            'active': 'on',
        })

        self.assertRedirects(response, reverse('offers:catalogue'))
        offre = Offre.objects.get(nom='Offre sans validité')
        self.assertIsNone(offre.duree_validite_mois)


class OffreUpdateViewTests(TestCase):
    def setUp(self):
        self.gestionnaire = creer_gestionnaire(username='gestionnaire_modifier_offre')
        self.offre = Offre.objects.create(
            nom='Offre à modifier', type_offre=Offre.TypeOffre.CARNET,
            prix=100, nombre_seances=11, duree_validite_mois=3,
        )
        self.client.force_login(self.gestionnaire)

    def test_propose_un_bouton_annuler_vers_le_catalogue(self):
        response = self.client.get(reverse('offers:offre_modifier', args=[self.offre.pk]))

        self.assertContains(response, 'Annuler')
        self.assertContains(response, reverse('offers:catalogue'))

    def test_modifie_la_duree_de_validite(self):
        response = self.client.post(reverse('offers:offre_modifier', args=[self.offre.pk]), {
            'nom': self.offre.nom,
            'type_offre': Offre.TypeOffre.CARNET,
            'description': '',
            'prix': '100',
            'nombre_seances': 11,
            'duree_validite_mois': 6,
            'active': 'on',
        })

        self.assertRedirects(response, reverse('offers:catalogue'))
        self.offre.refresh_from_db()
        self.assertEqual(self.offre.duree_validite_mois, 6)

    def test_un_membre_ne_peut_pas_modifier_une_offre(self):
        membre = User.objects.create_user(username='membre_modifier_offre', password='motdepasse123')
        self.client.force_login(membre)

        response = self.client.get(reverse('offers:offre_modifier', args=[self.offre.pk]))

        self.assertEqual(response.status_code, 403)


class OffreDeleteViewTests(TestCase):
    def setUp(self):
        self.gestionnaire = creer_gestionnaire(username='gestionnaire_supprimer_offre')
        self.offre = Offre.objects.create(
            nom='Offre à supprimer', type_offre=Offre.TypeOffre.CARNET,
            prix=100, nombre_seances=11, duree_validite_mois=3,
        )
        self.client.force_login(self.gestionnaire)

    def test_supprime_une_offre_jamais_achetee(self):
        response = self.client.post(reverse('offers:offre_supprimer', args=[self.offre.pk]))

        self.assertRedirects(response, reverse('offers:catalogue'))
        self.assertFalse(Offre.objects.filter(pk=self.offre.pk).exists())

    def test_refuse_de_supprimer_une_offre_deja_achetee(self):
        from apps.purchases.services import enregistrer_achat

        membre = User.objects.create(username='membre_a_achete')
        enregistrer_achat(membre=membre, offre=self.offre, prix_paye=100, saisi_par=self.gestionnaire)

        response = self.client.post(reverse('offers:offre_supprimer', args=[self.offre.pk]), follow=True)

        self.assertTrue(Offre.objects.filter(pk=self.offre.pk).exists())
        self.assertContains(response, 'achat')

    def test_un_membre_ne_peut_pas_supprimer_une_offre(self):
        membre = User.objects.create_user(username='membre_supprimer_offre', password='motdepasse123')
        self.client.force_login(membre)

        response = self.client.post(reverse('offers:offre_supprimer', args=[self.offre.pk]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Offre.objects.filter(pk=self.offre.pk).exists())
