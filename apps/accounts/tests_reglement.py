import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.bookings.models import Inscription
from apps.purchases.models import MouvementSeance
from apps.scheduling.models import Seance

from . import reglement
from .models import User


def _membre(username='alice', accepte=False, **kwargs):
    membre = User.objects.create_user(username=username, password='x', **kwargs)
    MouvementSeance.objects.create(membre=membre, delta=5, motif=MouvementSeance.Motif.ACHAT)
    if accepte:
        membre.accepter_reglement()
    return membre


def _seance():
    debut = timezone.now() + datetime.timedelta(days=1)
    return Seance.objects.create(
        nom='WOD', debut=debut, duree_minutes=60, capacite_max=10, delai_annulation_heures=12
    )


class ReglementAccepteTests(TestCase):
    def test_nouveau_compte_n_a_pas_accepte(self):
        self.assertFalse(_membre().reglement_a_jour)

    def test_accepter_enregistre_version_et_horodatage(self):
        membre = _membre()
        membre.accepter_reglement()
        membre.refresh_from_db()
        self.assertTrue(membre.reglement_a_jour)
        self.assertEqual(membre.reglement_version_acceptee, reglement.VERSION)
        self.assertIsNotNone(membre.reglement_accepte_le)

    def test_nouvelle_version_exige_une_nouvelle_acceptation(self):
        membre = _membre(accepte=True)
        membre.reglement_version_acceptee = 'ancienne'
        self.assertFalse(membre.reglement_a_jour)


class ReglementPageTests(TestCase):
    def test_lecture_publique(self):
        reponse = self.client.get(reverse('accounts:reglement'))
        self.assertContains(reponse, 'RÈGLEMENT INTÉRIEUR')

    def test_acceptation_exige_la_connexion(self):
        reponse = self.client.get(reverse('accounts:reglement_accepter'))
        self.assertEqual(reponse.status_code, 302)
        self.assertIn(reverse('accounts:login'), reponse.url)

    def test_post_sans_case_cochee_refuse(self):
        membre = _membre()
        self.client.force_login(membre)
        reponse = self.client.post(reverse('accounts:reglement_accepter'), {})
        self.assertEqual(reponse.status_code, 200)
        membre.refresh_from_db()
        self.assertFalse(membre.reglement_a_jour)

    def test_post_case_cochee_enregistre_et_redirige_vers_next(self):
        membre = _membre()
        self.client.force_login(membre)
        reponse = self.client.post(
            reverse('accounts:reglement_accepter'), {'accepte': 'on', 'next': '/calendrier/'}
        )
        self.assertRedirects(reponse, '/calendrier/', fetch_redirect_response=False)
        membre.refresh_from_db()
        self.assertTrue(membre.reglement_a_jour)

    def test_next_externe_ignore(self):
        membre = _membre()
        self.client.force_login(membre)
        reponse = self.client.post(
            reverse('accounts:reglement_accepter'), {'accepte': 'on', 'next': 'https://evil.example/'}
        )
        self.assertNotIn('evil', reponse.url)


class ReglementBloqueInscriptionTests(TestCase):
    def test_inscription_bloquee_tant_que_non_accepte(self):
        membre = _membre()
        seance = _seance()
        self.client.force_login(membre)
        reponse = self.client.post(reverse('bookings:inscrire', args=[seance.pk]))
        self.assertEqual(reponse.status_code, 302)
        self.assertIn(reverse('accounts:reglement_accepter'), reponse.url)
        self.assertFalse(Inscription.objects.filter(membre=membre).exists())

    def test_liste_attente_bloquee_aussi(self):
        membre = _membre()
        seance = _seance()
        self.client.force_login(membre)
        reponse = self.client.post(reverse('bookings:liste_attente_rejoindre', args=[seance.pk]))
        self.assertIn(reverse('accounts:reglement_accepter'), reponse.url)

    def test_inscription_possible_apres_acceptation(self):
        membre = _membre(accepte=True)
        seance = _seance()
        self.client.force_login(membre)
        self.client.post(reverse('bookings:inscrire', args=[seance.pk]))
        self.assertTrue(Inscription.objects.filter(membre=membre, seance=seance).exists())

    def test_desinscription_jamais_bloquee(self):
        membre = _membre()
        seance = _seance()
        Inscription.objects.create(membre=membre, seance=seance, auteur=membre)
        self.client.force_login(membre)
        reponse = self.client.post(reverse('bookings:desinscrire', args=[seance.pk]))
        self.assertNotIn(reverse('accounts:reglement_accepter'), reponse.url)


class ReglementPremiereConnexionTests(TestCase):
    def test_premiere_connexion_redirige_vers_acceptation(self):
        _membre(username='nouveau')
        reponse = self.client.post(
            reverse('accounts:login'), {'username': 'nouveau', 'password': 'x'}
        )
        self.assertIn(reverse('accounts:reglement_accepter'), reponse.url)

    def test_connexion_suivante_sans_acceptation_ne_bloque_pas(self):
        membre = _membre(username='ancien')
        membre.last_login = timezone.now()
        membre.save()
        reponse = self.client.post(reverse('accounts:login'), {'username': 'ancien', 'password': 'x'})
        self.assertNotIn(reverse('accounts:reglement_accepter'), reponse.url)
