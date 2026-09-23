import datetime
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.actualites.models import Actualite
from apps.bookings.services import enregistrer_inscription, marquer_non_presente
from apps.purchases.models import MouvementSeance

from .forms import SeanceForm
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


class DateHeureOuvertureInscriptionsTests(TestCase):
    def test_ouvre_le_mercredi_precedent_a_21h(self):
        seance = Seance(debut=timezone.make_aware(datetime.datetime(2027, 3, 15, 18, 0)))

        attendu = timezone.make_aware(datetime.datetime(2027, 3, 10, 21, 0))
        self.assertEqual(seance.date_heure_ouverture_inscriptions, attendu)


class InscriptionsOuvertesTests(TestCase):
    def setUp(self):
        self.seance = Seance(debut=timezone.make_aware(datetime.datetime(2027, 3, 15, 18, 0)))

    @patch('django.utils.timezone.now')
    def test_fermees_avant_21h_le_mercredi_d_ouverture(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime.datetime(2027, 3, 10, 20, 59))

        self.assertFalse(self.seance.inscriptions_ouvertes)

    @patch('django.utils.timezone.now')
    def test_ouvertes_a_21h_pile_le_mercredi_d_ouverture(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime.datetime(2027, 3, 10, 21, 0))

        self.assertTrue(self.seance.inscriptions_ouvertes)

    @patch('django.utils.timezone.now')
    def test_fermees_la_veille_meme_tard_le_soir(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime.datetime(2027, 3, 9, 23, 59))

        self.assertFalse(self.seance.inscriptions_ouvertes)

    @patch('django.utils.timezone.now')
    def test_restent_ouvertes_les_jours_suivants(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime.datetime(2027, 3, 12, 10, 0))

        self.assertTrue(self.seance.inscriptions_ouvertes)


class SeanceDetailMessageOuvertureTests(TestCase):
    def test_affiche_l_heure_d_ouverture_en_plus_de_la_date(self):
        membre = User.objects.create_user(username='membre_fiche_ouverture', password='motdepasse123')
        seance = Seance.objects.create(
            nom='WOD', debut=timezone.now() + datetime.timedelta(days=20),
        )
        self.client.force_login(membre)

        response = self.client.get(reverse('scheduling:seance_detail', kwargs={'pk': seance.pk}))

        self.assertContains(response, '21:00')


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


class SeanceDetailPaiementWeroTests(TestCase):
    def test_la_carte_de_paiement_wero_s_affiche_si_le_credit_est_insuffisant(self):
        membre = User.objects.create_user(username='membre_sans_credit_wero', password='motdepasse123')
        seance = Seance.objects.create(nom='WOD', debut=timezone.now() + datetime.timedelta(days=2))
        self.client.force_login(membre)

        response = self.client.get(reverse('scheduling:seance_detail', kwargs={'pk': seance.pk}))

        self.assertContains(response, settings.RECEPTIONNAIRE_PAIEMENTS_TEL)
        self.assertContains(response, 'Wero')

    def test_la_carte_de_paiement_wero_a_un_encadre_distinct(self):
        membre = User.objects.create_user(username='membre_sans_credit_wero_style', password='motdepasse123')
        seance = Seance.objects.create(nom='WOD', debut=timezone.now() + datetime.timedelta(days=2))
        self.client.force_login(membre)

        response = self.client.get(reverse('scheduling:seance_detail', kwargs={'pk': seance.pk}))

        self.assertContains(response, 'carte-paiement-wero')

    def test_la_carte_de_paiement_wero_parle_de_seances_pas_de_carnet(self):
        membre = User.objects.create_user(username='membre_sans_credit_wero_vocab', password='motdepasse123')
        seance = Seance.objects.create(nom='WOD', debut=timezone.now() + datetime.timedelta(days=2))
        self.client.force_login(membre)

        response = self.client.get(reverse('scheduling:seance_detail', kwargs={'pk': seance.pk}))

        self.assertContains(response, 'séances')
        self.assertNotContains(response, 'carnet')

    @override_settings(RECEPTIONNAIRE_PAIEMENTS_TEL='')
    def test_le_bouton_normal_s_affiche_si_la_config_wero_est_absente(self):
        membre = User.objects.create_user(username='membre_sans_credit_sans_config', password='motdepasse123')
        seance = Seance.objects.create(nom='WOD', debut=timezone.now() + datetime.timedelta(days=2))
        self.client.force_login(membre)

        response = self.client.get(reverse('scheduling:seance_detail', kwargs={'pk': seance.pk}))

        self.assertContains(response, "S'inscrire")
        self.assertNotContains(response, 'carte-paiement-wero')

    def test_le_bouton_s_inscrire_n_apparait_pas_si_le_credit_est_insuffisant(self):
        membre = User.objects.create_user(username='membre_sans_credit_bouton', password='motdepasse123')
        seance = Seance.objects.create(nom='WOD', debut=timezone.now() + datetime.timedelta(days=2))
        self.client.force_login(membre)

        response = self.client.get(reverse('scheduling:seance_detail', kwargs={'pk': seance.pk}))

        self.assertNotContains(response, "S'inscrire")

    def test_la_carte_de_paiement_wero_ne_s_affiche_pas_si_le_credit_est_suffisant(self):
        membre = User.objects.create_user(username='membre_avec_credit_wero', password='motdepasse123')
        MouvementSeance.objects.create(membre=membre, delta=5, motif=MouvementSeance.Motif.ACHAT)
        seance = Seance.objects.create(nom='WOD', debut=timezone.now() + datetime.timedelta(days=2))
        self.client.force_login(membre)

        response = self.client.get(reverse('scheduling:seance_detail', kwargs={'pk': seance.pk}))

        self.assertNotContains(response, settings.RECEPTIONNAIRE_PAIEMENTS_TEL)
        self.assertContains(response, "S'inscrire")

    def test_la_carte_de_paiement_wero_ne_s_affiche_pas_pour_un_gestionnaire(self):
        gestionnaire = User.objects.create_user(
            username='gestionnaire_wero', password='motdepasse123', role=User.Role.GESTIONNAIRE
        )
        seance = Seance.objects.create(nom='WOD', debut=timezone.now() + datetime.timedelta(days=2))
        self.client.force_login(gestionnaire)

        response = self.client.get(reverse('scheduling:seance_detail', kwargs={'pk': seance.pk}))

        self.assertNotContains(response, settings.RECEPTIONNAIRE_PAIEMENTS_TEL)

    def test_la_carte_de_paiement_wero_s_affiche_aussi_en_liste_d_attente(self):
        membre_complet = User.objects.create_user(username='membre_complet_wod', password='motdepasse123')
        MouvementSeance.objects.create(membre=membre_complet, delta=5, motif=MouvementSeance.Motif.ACHAT)
        seance = Seance.objects.create(
            nom='WOD', debut=timezone.now() + datetime.timedelta(days=2), capacite_max=1,
        )
        enregistrer_inscription(membre=membre_complet, seance=seance, auteur=membre_complet)
        membre_sans_credit = User.objects.create_user(username='membre_sans_credit_attente', password='motdepasse123')
        self.client.force_login(membre_sans_credit)

        response = self.client.get(reverse('scheduling:seance_detail', kwargs={'pk': seance.pk}))

        self.assertContains(response, settings.RECEPTIONNAIRE_PAIEMENTS_TEL)
        self.assertNotContains(response, "liste d'attente")


class SeanceDetailParticipantCliquableTests(TestCase):
    def setUp(self):
        self.coach = User.objects.create_user(
            username='coach_participant_clic', password='motdepasse123', role=User.Role.GESTIONNAIRE
        )
        self.membre = User.objects.create(username='membre_participant_clic')
        MouvementSeance.objects.create(membre=self.membre, delta=5, motif=MouvementSeance.Motif.ACHAT)
        self.seance = Seance.objects.create(
            nom='WOD', debut=timezone.now() + datetime.timedelta(days=2), coach=self.coach,
        )
        enregistrer_inscription(membre=self.membre, seance=self.seance, auteur=self.membre)

    def test_le_gestionnaire_peut_cliquer_sur_un_participant(self):
        self.client.force_login(self.coach)

        response = self.client.get(reverse('scheduling:seance_detail', kwargs={'pk': self.seance.pk}))

        self.assertContains(response, 'card-clickable')
        self.assertContains(
            response, f'data-href="{reverse("accounts:membre_modifier", kwargs={"pk": self.membre.pk})}"'
        )

    def test_un_membre_ne_peut_pas_cliquer_sur_un_participant(self):
        self.client.force_login(self.membre)

        response = self.client.get(reverse('scheduling:seance_detail', kwargs={'pk': self.seance.pk}))

        self.assertNotContains(response, 'data-href="/comptes/membres/')
        self.assertNotContains(
            response, reverse('accounts:membre_modifier', kwargs={'pk': self.membre.pk})
        )


class SeanceDetailNonPresenteTests(TestCase):
    def setUp(self):
        self.coach = User.objects.create_user(
            username='coach_non_presente_liste', password='motdepasse123', role=User.Role.GESTIONNAIRE
        )
        self.membre = User.objects.create(username='membre_non_presente_liste')
        MouvementSeance.objects.create(membre=self.membre, delta=5, motif=MouvementSeance.Motif.ACHAT)
        self.seance = Seance.objects.create(
            nom='WOD', debut=timezone.now() - datetime.timedelta(hours=1), coach=self.coach,
        )
        self.inscription = enregistrer_inscription(membre=self.membre, seance=self.seance, auteur=self.membre)
        marquer_non_presente(self.inscription, auteur=self.coach)
        self.client.force_login(self.coach)

    def test_le_membre_non_presente_reste_dans_la_liste(self):
        response = self.client.get(reverse('scheduling:seance_detail', kwargs={'pk': self.seance.pk}))

        self.assertContains(response, self.membre.username)

    def test_la_card_du_membre_non_presente_a_un_fond_rouge(self):
        response = self.client.get(reverse('scheduling:seance_detail', kwargs={'pk': self.seance.pk}))

        self.assertContains(response, 'card-non-presente')


class SeanceFormCoachQuerysetTests(TestCase):
    def test_propose_les_coachs_gestionnaires_et_les_coachs_simples(self):
        gestionnaire = User.objects.create(username='gestionnaire_form', role=User.Role.GESTIONNAIRE)
        coach_simple = User.objects.create(username='coach_simple_form', role=User.Role.COACH)
        User.objects.create(username='membre_form', role=User.Role.MEMBRE)

        form = SeanceForm()

        self.assertIn(gestionnaire, form.fields['coach'].queryset)
        self.assertIn(coach_simple, form.fields['coach'].queryset)
        self.assertEqual(form.fields['coach'].queryset.count(), 2)


class SeanceDetailCoachSimpleTests(TestCase):
    def setUp(self):
        self.coach_simple = User.objects.create_user(
            username='coach_simple_detail', password='motdepasse123', role=User.Role.COACH
        )
        self.membre = User.objects.create(username='membre_detail_coach_simple')
        MouvementSeance.objects.create(membre=self.membre, delta=5, motif=MouvementSeance.Motif.ACHAT)
        self.client.force_login(self.coach_simple)

    def test_peut_marquer_non_presente_sur_une_seance_passee(self):
        seance = Seance.objects.create(
            nom='WOD', debut=timezone.now() - datetime.timedelta(hours=1),
        )
        enregistrer_inscription(membre=self.membre, seance=seance, auteur=self.membre)

        response = self.client.get(reverse('scheduling:seance_detail', kwargs={'pk': seance.pk}))

        self.assertContains(response, 'Non présent(e)')
        self.assertNotContains(response, 'Désinscrire')

    def test_ne_voit_pas_les_boutons_d_ajustement_de_solde(self):
        seance = Seance.objects.create(
            nom='WOD', debut=timezone.now() - datetime.timedelta(hours=1),
        )
        enregistrer_inscription(membre=self.membre, seance=seance, auteur=self.membre)

        response = self.client.get(reverse('scheduling:seance_detail', kwargs={'pk': seance.pk}))

        self.assertNotContains(response, 'purchases:ajuster_solde')
        self.assertNotContains(response, '/solde/ajuster/')

    def test_ne_voit_aucun_bouton_sur_une_seance_a_venir(self):
        seance = Seance.objects.create(
            nom='WOD', debut=timezone.now() + datetime.timedelta(days=2),
        )
        enregistrer_inscription(membre=self.membre, seance=seance, auteur=self.membre)

        response = self.client.get(reverse('scheduling:seance_detail', kwargs={'pk': seance.pk}))

        self.assertNotContains(response, 'Non présent(e)')
        self.assertNotContains(response, 'Désinscrire')

    def test_ne_peut_pas_cliquer_sur_la_fiche_d_un_participant(self):
        seance = Seance.objects.create(
            nom='WOD', debut=timezone.now() - datetime.timedelta(hours=1),
        )
        enregistrer_inscription(membre=self.membre, seance=seance, auteur=self.membre)

        response = self.client.get(reverse('scheduling:seance_detail', kwargs={'pk': seance.pk}))

        self.assertNotContains(response, 'data-href="/comptes/membres/')


class NotifierOuverturesInscriptionsRespecteL_HeureTests(TestCase):
    def setUp(self):
        self.seance = Seance.objects.create(
            nom='WOD',
            debut=timezone.make_aware(datetime.datetime(2027, 3, 15, 18, 0)),
            duree_minutes=60,
            capacite_max=10,
            delai_annulation_heures=24,
        )

    @patch('django.utils.timezone.now')
    def test_n_envoie_rien_avant_21h_le_jour_d_ouverture(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime.datetime(2027, 3, 10, 20, 59))

        call_command('notifier_ouvertures_inscriptions')

        self.seance.refresh_from_db()
        self.assertFalse(self.seance.notification_ouverture_envoyee)

    @patch('django.utils.timezone.now')
    def test_envoie_a_partir_de_21h_le_jour_d_ouverture(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime.datetime(2027, 3, 10, 21, 0))

        call_command('notifier_ouvertures_inscriptions')

        self.seance.refresh_from_db()
        self.assertTrue(self.seance.notification_ouverture_envoyee)


class NotifierOuverturesInscriptionsEmailTests(TestCase):
    def setUp(self):
        self.seance = Seance.objects.create(
            nom='WOD',
            debut=timezone.now() + datetime.timedelta(days=1),
            duree_minutes=60,
            capacite_max=10,
            delai_annulation_heures=24,
        )

    def test_envoie_un_email_au_membre_par_defaut(self):
        membre = User.objects.create_user(
            username='membre_email_ouverture', password='motdepasse123',
            role=User.Role.MEMBRE, email='membre@example.com',
        )

        call_command('notifier_ouvertures_inscriptions')

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(membre.email, mail.outbox[0].to)
        self.assertIn('WOD', mail.outbox[0].subject + mail.outbox[0].body)

    def test_n_envoie_pas_si_le_membre_a_refuse_les_emails(self):
        User.objects.create_user(
            username='membre_refuse_email', password='motdepasse123',
            role=User.Role.MEMBRE, email='refuse@example.com', email_ouverture_seance=False,
        )

        call_command('notifier_ouvertures_inscriptions')

        self.assertEqual(len(mail.outbox), 0)

    def test_n_envoie_pas_a_un_membre_sans_email(self):
        User.objects.create_user(username='membre_sans_email', password='motdepasse123', role=User.Role.MEMBRE)

        call_command('notifier_ouvertures_inscriptions')

        self.assertEqual(len(mail.outbox), 0)

    def test_n_envoie_pas_a_un_coach(self):
        User.objects.create_user(
            username='coach_pas_email', password='motdepasse123',
            role=User.Role.COACH, email='coach@example.com',
        )

        call_command('notifier_ouvertures_inscriptions')

        self.assertEqual(len(mail.outbox), 0)

    @patch('apps.scheduling.management.commands.notifier_ouvertures_inscriptions.notifier_membres')
    def test_envoie_toujours_la_notification_ntfy_partagee(self, mock_notifier_membres):
        User.objects.create_user(
            username='membre_ntfy_check', password='motdepasse123',
            role=User.Role.MEMBRE, email='ntfy@example.com',
        )

        call_command('notifier_ouvertures_inscriptions')

        mock_notifier_membres.assert_called_once()


class CalendrierActualitesTests(TestCase):
    def setUp(self):
        self.membre = User.objects.create_user(username='membre_calendrier_actu', password='motdepasse123')
        self.client.force_login(self.membre)

    def test_affiche_une_actualite_active_avec_croix_de_fermeture(self):
        aujourd_hui = timezone.localdate()
        Actualite.objects.create(
            texte='Fermeture exceptionnelle',
            date_debut=aujourd_hui,
            date_fin=aujourd_hui + datetime.timedelta(days=5),
        )

        response = self.client.get(reverse('scheduling:calendrier'))

        self.assertContains(response, 'Fermeture exceptionnelle')
        self.assertContains(response, 'bandeau-actualites-fermer')

    def test_le_bouton_pointe_directement_vers_la_cible_pour_un_connecte(self):
        aujourd_hui = timezone.localdate()
        Actualite.objects.create(
            texte='Nouvelle offre disponible !',
            date_debut=aujourd_hui,
            date_fin=aujourd_hui + datetime.timedelta(days=5),
            cible=Actualite.Cible.OFFRES,
        )

        response = self.client.get(reverse('scheduling:calendrier'))

        self.assertContains(response, reverse('offers:catalogue'))
        self.assertNotContains(response, f"{reverse('accounts:login')}?next=")

    def test_pas_de_bandeau_si_aucune_actualite(self):
        response = self.client.get(reverse('scheduling:calendrier'))

        self.assertNotContains(response, 'bandeau-actualites')


class CalendrierSemaineIndicateurJoursTests(TestCase):
    def test_l_indicateur_de_defilement_est_present(self):
        membre = User.objects.create_user(username='membre_calendrier_indicateur', password='motdepasse123')
        self.client.force_login(membre)

        response = self.client.get(reverse('scheduling:calendrier'))

        self.assertContains(response, 'jours-semaine-chevron')

    def test_le_chevron_est_un_bouton_cliquable(self):
        membre = User.objects.create_user(username='membre_calendrier_chevron_bouton', password='motdepasse123')
        self.client.force_login(membre)

        response = self.client.get(reverse('scheduling:calendrier'))

        self.assertContains(response, '<button type="button" class="jours-semaine-chevron"')


class AccesAnonymeCalendrierTests(TestCase):
    def test_le_calendrier_redirige_vers_la_connexion_si_anonyme(self):
        response = self.client.get(reverse('scheduling:calendrier'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_le_calendrier_mensuel_redirige_vers_la_connexion_si_anonyme(self):
        response = self.client.get(reverse('scheduling:calendrier_mois'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_la_fiche_seance_redirige_vers_la_connexion_si_anonyme(self):
        seance = Seance.objects.create(nom='WOD', debut=timezone.now() + datetime.timedelta(days=1))

        response = self.client.get(reverse('scheduling:seance_detail', kwargs={'pk': seance.pk}))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)
