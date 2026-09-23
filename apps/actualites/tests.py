import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User

from .models import Actualite


def creer_actualite(**kwargs):
    aujourd_hui = timezone.localdate()
    kwargs.setdefault('texte', 'Fermeture exceptionnelle du 1er au 5 janvier.')
    kwargs.setdefault('date_debut', aujourd_hui - datetime.timedelta(days=1))
    kwargs.setdefault('date_fin', aujourd_hui + datetime.timedelta(days=1))
    return Actualite.objects.create(**kwargs)


class ActualiteQuerySetTests(TestCase):
    def test_actives_renvoie_une_actualite_en_cours(self):
        actualite = creer_actualite()

        self.assertIn(actualite, Actualite.objects.actives())

    def test_actives_exclut_une_actualite_passee(self):
        aujourd_hui = timezone.localdate()
        actualite = creer_actualite(
            date_debut=aujourd_hui - datetime.timedelta(days=10),
            date_fin=aujourd_hui - datetime.timedelta(days=5),
        )

        self.assertNotIn(actualite, Actualite.objects.actives())

    def test_actives_exclut_une_actualite_future(self):
        aujourd_hui = timezone.localdate()
        actualite = creer_actualite(
            date_debut=aujourd_hui + datetime.timedelta(days=5),
            date_fin=aujourd_hui + datetime.timedelta(days=10),
        )

        self.assertNotIn(actualite, Actualite.objects.actives())


class ActualiteValidationTests(TestCase):
    def test_refuse_si_la_date_fin_precede_la_date_debut(self):
        aujourd_hui = timezone.localdate()
        actualite = Actualite(
            texte='Test',
            date_debut=aujourd_hui,
            date_fin=aujourd_hui - datetime.timedelta(days=1),
        )

        with self.assertRaises(ValidationError):
            actualite.full_clean()

    def test_accepte_une_troisieme_actualite_sur_la_meme_periode(self):
        creer_actualite()
        creer_actualite()
        troisieme = Actualite(
            texte='Troisième',
            date_debut=timezone.localdate(),
            date_fin=timezone.localdate() + datetime.timedelta(days=1),
        )

        troisieme.full_clean()

    def test_refuse_une_quatrieme_actualite_sur_la_meme_periode(self):
        creer_actualite()
        creer_actualite()
        creer_actualite()
        quatrieme = Actualite(
            texte='Quatrième',
            date_debut=timezone.localdate(),
            date_fin=timezone.localdate() + datetime.timedelta(days=1),
        )

        with self.assertRaises(ValidationError):
            quatrieme.full_clean()

    def test_accepte_une_quatrieme_actualite_sur_une_periode_differente(self):
        creer_actualite()
        creer_actualite()
        creer_actualite()
        aujourd_hui = timezone.localdate()
        quatrieme = Actualite(
            texte='Plus tard',
            date_debut=aujourd_hui + datetime.timedelta(days=30),
            date_fin=aujourd_hui + datetime.timedelta(days=31),
        )

        quatrieme.full_clean()


def creer_gestionnaire(**kwargs):
    kwargs.setdefault('username', 'gestionnaire_actu')
    kwargs.setdefault('role', User.Role.GESTIONNAIRE)
    return User.objects.create_user(password='motdepasse123', **kwargs)


class ActualiteListViewTests(TestCase):
    def test_necessite_d_etre_gestionnaire(self):
        membre = User.objects.create_user(username='membre_actu', password='motdepasse123')
        self.client.force_login(membre)

        response = self.client.get(reverse('actualites:liste'))

        self.assertEqual(response.status_code, 403)

    def test_un_gestionnaire_voit_la_liste(self):
        gestionnaire = creer_gestionnaire()
        actualite = creer_actualite()
        self.client.force_login(gestionnaire)

        response = self.client.get(reverse('actualites:liste'))

        self.assertContains(response, actualite.texte)


class ActualiteCreateViewTests(TestCase):
    def setUp(self):
        self.gestionnaire = creer_gestionnaire()
        self.client.force_login(self.gestionnaire)

    def test_un_gestionnaire_peut_creer_une_actualite(self):
        aujourd_hui = timezone.localdate()
        response = self.client.post(reverse('actualites:creer'), {
            'texte': 'Nouvelle offre spéciale rentrée !',
            'date_debut': aujourd_hui.isoformat(),
            'date_fin': (aujourd_hui + datetime.timedelta(days=15)).isoformat(),
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Actualite.objects.filter(texte='Nouvelle offre spéciale rentrée !').exists())

    def test_refuse_une_quatrieme_actualite_concurrente(self):
        creer_actualite()
        creer_actualite()
        creer_actualite()
        aujourd_hui = timezone.localdate()

        response = self.client.post(reverse('actualites:creer'), {
            'texte': 'Refusée',
            'date_debut': aujourd_hui.isoformat(),
            'date_fin': (aujourd_hui + datetime.timedelta(days=1)).isoformat(),
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Actualite.objects.filter(texte='Refusée').exists())


class ActualiteDeleteViewTests(TestCase):
    def test_un_gestionnaire_peut_supprimer_une_actualite(self):
        gestionnaire = creer_gestionnaire()
        actualite = creer_actualite()
        self.client.force_login(gestionnaire)

        self.client.post(reverse('actualites:supprimer', args=[actualite.pk]))

        self.assertFalse(Actualite.objects.filter(pk=actualite.pk).exists())
