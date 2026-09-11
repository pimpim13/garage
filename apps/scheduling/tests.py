import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

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
