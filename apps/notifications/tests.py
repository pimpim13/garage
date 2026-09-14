import datetime
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.scheduling.models import Seance

from .ntfy import notifier_coach, notifier_evenement_seance


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


class NotifierEvenementSeanceTests(TestCase):
    def setUp(self):
        self.coach = User.objects.create(username='coach_evt', role=User.Role.COACH)
        self.gestionnaire = User.objects.create(username='gestionnaire_evt', role=User.Role.GESTIONNAIRE)
        self.seance = Seance.objects.create(
            nom='WOD', debut=timezone.now() + datetime.timedelta(days=2), coach=self.coach,
        )

    def _urls_appelees(self, mock_post):
        return [call.args[0] for call in mock_post.call_args_list]

    @patch('apps.notifications.ntfy.requests.post')
    def test_notifie_le_coach_assigne_a_la_seance(self, mock_post):
        notifier_evenement_seance(self.seance, "Message", 'notifie_inscription')

        self.assertTrue(any(self.coach.topic_ntfy_coach in url for url in self._urls_appelees(mock_post)))

    @patch('apps.notifications.ntfy.requests.post')
    def test_le_gestionnaire_ne_recoit_rien_par_defaut_s_il_ne_suit_personne(self, mock_post):
        notifier_evenement_seance(self.seance, "Message", 'notifie_inscription')

        self.assertFalse(any(self.gestionnaire.topic_ntfy_coach in url for url in self._urls_appelees(mock_post)))

    @patch('apps.notifications.ntfy.requests.post')
    def test_ne_notifie_pas_le_coach_si_sa_preference_est_desactivee(self, mock_post):
        self.coach.notifie_inscription = False
        self.coach.save(update_fields=['notifie_inscription'])

        notifier_evenement_seance(self.seance, "Message", 'notifie_inscription')

        self.assertFalse(any(self.coach.topic_ntfy_coach in url for url in self._urls_appelees(mock_post)))

    @patch('apps.notifications.ntfy.requests.post')
    def test_ne_notifie_pas_le_gestionnaire_si_sa_preference_est_desactivee(self, mock_post):
        self.gestionnaire.coachs_suivis.add(self.coach)
        self.gestionnaire.notifie_inscription = False
        self.gestionnaire.save(update_fields=['notifie_inscription'])

        notifier_evenement_seance(self.seance, "Message", 'notifie_inscription')

        self.assertFalse(any(self.gestionnaire.topic_ntfy_coach in url for url in self._urls_appelees(mock_post)))

    @patch('apps.notifications.ntfy.requests.post')
    def test_gestionnaire_qui_suit_un_autre_coach_n_est_pas_notifie(self, mock_post):
        autre_coach = User.objects.create(username='autre_coach_evt', role=User.Role.COACH)
        self.gestionnaire.coachs_suivis.add(autre_coach)

        notifier_evenement_seance(self.seance, "Message", 'notifie_inscription')

        self.assertFalse(any(self.gestionnaire.topic_ntfy_coach in url for url in self._urls_appelees(mock_post)))

    @patch('apps.notifications.ntfy.requests.post')
    def test_gestionnaire_est_notifie_pour_le_coach_qu_il_suit(self, mock_post):
        self.gestionnaire.coachs_suivis.add(self.coach)

        notifier_evenement_seance(self.seance, "Message", 'notifie_inscription')

        self.assertTrue(any(self.gestionnaire.topic_ntfy_coach in url for url in self._urls_appelees(mock_post)))

    @patch('apps.notifications.ntfy.requests.post')
    def test_un_coach_n_est_pas_notifie_pour_la_seance_d_un_autre_coach(self, mock_post):
        autre_coach = User.objects.create(username='autre_coach_isole', role=User.Role.COACH)

        notifier_evenement_seance(self.seance, "Message", 'notifie_inscription')

        self.assertFalse(any(autre_coach.topic_ntfy_coach in url for url in self._urls_appelees(mock_post)))

    @patch('apps.notifications.ntfy.requests.post')
    def test_ne_notifie_pas_deux_fois_si_le_coach_de_la_seance_est_gestionnaire(self, mock_post):
        seance_geree = Seance.objects.create(
            nom='WOD2', debut=timezone.now() + datetime.timedelta(days=2), coach=self.gestionnaire,
        )

        notifier_evenement_seance(seance_geree, "Message", 'notifie_inscription')

        occurrences = sum(
            1 for url in self._urls_appelees(mock_post) if self.gestionnaire.topic_ntfy_coach in url
        )
        self.assertEqual(occurrences, 1)

    @patch('apps.notifications.ntfy.requests.post')
    def test_respecte_le_champ_de_preference_demande(self, mock_post):
        self.coach.notifie_seance_complete = False
        self.coach.save(update_fields=['notifie_seance_complete'])

        notifier_evenement_seance(self.seance, "Message", 'notifie_seance_complete')

        self.assertFalse(any(self.coach.topic_ntfy_coach in url for url in self._urls_appelees(mock_post)))


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


class PreferencesViewCoachEvenementsTests(TestCase):
    def setUp(self):
        self.coach = User.objects.create_user(
            username='coach_pref_evt', password='motdepasse123', role=User.Role.COACH
        )
        self.client.force_login(self.coach)

    def test_affiche_les_4_cases_a_cocher(self):
        response = self.client.get(reverse('notifications:preferences'))

        self.assertContains(response, 'name="notifie_inscription"')
        self.assertContains(response, 'name="notifie_desinscription"')
        self.assertContains(response, 'name="notifie_promotion_automatique"')
        self.assertContains(response, 'name="notifie_seance_complete"')

    def test_ne_montre_pas_le_selecteur_de_coachs_suivis(self):
        response = self.client.get(reverse('notifications:preferences'))

        self.assertNotContains(response, 'name="coachs_suivis"')

    def test_decocher_une_case_desactive_la_preference(self):
        self.client.post(reverse('notifications:preferences'), {
            'notifie_inscription': 'on',
            'notifie_desinscription': 'on',
            'notifie_promotion_automatique': 'on',
        })

        self.coach.refresh_from_db()
        self.assertTrue(self.coach.notifie_inscription)
        self.assertFalse(self.coach.notifie_seance_complete)


class PreferencesViewGestionnaireEvenementsTests(TestCase):
    def setUp(self):
        self.gestionnaire = User.objects.create_user(
            username='gestionnaire_pref_evt', password='motdepasse123', role=User.Role.GESTIONNAIRE
        )
        self.coach_a = User.objects.create(username='coach_liste_a', role=User.Role.COACH)
        self.coach_b = User.objects.create(username='coach_liste_b', role=User.Role.COACH)
        self.client.force_login(self.gestionnaire)

    def test_affiche_la_liste_des_coachs_a_suivre(self):
        response = self.client.get(reverse('notifications:preferences'))

        self.assertContains(response, 'coach_liste_a')
        self.assertContains(response, 'coach_liste_b')

    def test_ne_propose_pas_de_se_suivre_lui_meme(self):
        response = self.client.get(reverse('notifications:preferences'))

        self.assertNotContains(response, f'value="{self.gestionnaire.pk}"')

    def test_selectionner_des_coachs_les_enregistre_comme_suivis(self):
        self.client.post(reverse('notifications:preferences'), {
            'notifie_inscription': 'on',
            'notifie_desinscription': 'on',
            'notifie_promotion_automatique': 'on',
            'notifie_seance_complete': 'on',
            'coachs_suivis': [str(self.coach_a.pk)],
        })

        self.gestionnaire.refresh_from_db()
        self.assertEqual(list(self.gestionnaire.coachs_suivis.all()), [self.coach_a])

    def test_ne_rien_selectionner_vide_la_liste_des_suivis(self):
        self.gestionnaire.coachs_suivis.add(self.coach_a)

        self.client.post(reverse('notifications:preferences'), {
            'notifie_inscription': 'on',
        })

        self.gestionnaire.refresh_from_db()
        self.assertEqual(list(self.gestionnaire.coachs_suivis.all()), [])

    def test_une_valeur_invalide_ne_fait_pas_planter_la_vue(self):
        response = self.client.post(reverse('notifications:preferences'), {
            'notifie_inscription': 'on',
            'coachs_suivis': ['', 'pas-un-id'],
        })

        self.assertEqual(response.status_code, 302)
        self.gestionnaire.refresh_from_db()
        self.assertEqual(list(self.gestionnaire.coachs_suivis.all()), [])
