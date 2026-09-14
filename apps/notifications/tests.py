from unittest.mock import patch

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User

from .ntfy import notifier_coach


class NotifierCoachTests(TestCase):
    @patch('apps.notifications.ntfy.requests.post')
    def test_envoie_au_topic_individuel_du_coach(self, mock_post):
        coach = User.objects.create(username='coach_ntfy', role=User.Role.COACH)

        notifier_coach(coach, "Séance complète.")

        mock_post.assert_called_once()
        url_appelee = mock_post.call_args.args[0]
        self.assertIn(coach.topic_ntfy_coach, url_appelee)

    @patch('apps.notifications.ntfy.requests.post')
    def test_n_envoie_rien_si_le_coach_est_none(self, mock_post):
        notifier_coach(None, "Séance complète.")

        mock_post.assert_not_called()

    @patch('apps.notifications.ntfy.requests.post')
    def test_n_envoie_rien_si_le_coach_n_a_pas_de_topic(self, mock_post):
        membre = User.objects.create(username='membre_sans_topic', role=User.Role.MEMBRE)

        notifier_coach(membre, "Séance complète.")

        mock_post.assert_not_called()


class PreferencesViewAccesTests(TestCase):
    def test_necessite_d_etre_connecte(self):
        response = self.client.get(reverse('notifications:preferences'))

        self.assertNotEqual(response.status_code, 200)


class PreferencesViewMembreTests(TestCase):
    def setUp(self):
        self.membre = User.objects.create_user(
            username='membre_pref_notif', password='motdepasse123', role=User.Role.MEMBRE
        )
        self.client.force_login(self.membre)

    def test_affiche_la_case_a_cocher_cochee_par_defaut(self):
        response = self.client.get(reverse('notifications:preferences'))

        self.assertContains(response, 'checked')
        self.assertContains(response, "email")

    def test_affiche_le_topic_ntfy_partage_des_membres(self):
        response = self.client.get(reverse('notifications:preferences'))

        self.assertContains(response, settings.NTFY_TOPIC_MEMBRES)

    def test_affiche_les_liens_app_store_et_play_store(self):
        response = self.client.get(reverse('notifications:preferences'))

        self.assertContains(response, 'apps.apple.com')
        self.assertContains(response, 'play.google.com')

    def test_ne_montre_pas_de_topic_ntfy_coach(self):
        response = self.client.get(reverse('notifications:preferences'))

        self.assertNotContains(response, 'garage-coach-')

    def test_decocher_desactive_le_consentement(self):
        self.client.post(reverse('notifications:preferences'), {})

        self.membre.refresh_from_db()
        self.assertFalse(self.membre.accepte_emails)

    def test_cocher_active_le_consentement(self):
        self.membre.accepte_emails = False
        self.membre.save(update_fields=['accepte_emails'])

        self.client.post(reverse('notifications:preferences'), {'accepte_emails': 'on'})

        self.membre.refresh_from_db()
        self.assertTrue(self.membre.accepte_emails)


class PreferencesViewCoachTests(TestCase):
    def test_affiche_le_topic_ntfy_individuel_du_coach(self):
        coach = User.objects.create_user(username='coach_pref_notif', password='motdepasse123', role=User.Role.COACH)
        self.client.force_login(coach)

        response = self.client.get(reverse('notifications:preferences'))

        self.assertContains(response, coach.topic_ntfy_coach)

    def test_ne_propose_pas_la_case_a_cocher_email(self):
        coach = User.objects.create_user(
            username='coach_sans_case_email', password='motdepasse123', role=User.Role.COACH
        )
        self.client.force_login(coach)

        response = self.client.get(reverse('notifications:preferences'))

        self.assertNotContains(response, 'name="accepte_emails"')
