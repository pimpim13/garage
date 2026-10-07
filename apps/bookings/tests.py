import datetime
from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.purchases.models import MouvementSeance
from apps.purchases.services import solde_seances
from apps.scheduling.models import Seance

from .models import Inscription, MouvementJoker
from .services import (
    attribuer_joker,
    attribuer_joker_initial,
    enregistrer_desinscription,
    enregistrer_inscription,
    historique_jokers,
    marquer_non_presente,
    peut_s_inscrire,
    permuter_inscription,
    promouvoir_liste_attente,
    seances_permutables,
    retirer_joker,
    solde_jokers,
)

User = get_user_model()


class PeutSInscrireTests(TestCase):
    def test_refuse_si_le_solde_apres_inscription_serait_sous_la_tolerance(self):
        membre = User.objects.create(username='sans_credit', tolerance_seances_negatives=0)

        self.assertFalse(peut_s_inscrire(membre))

    def test_autorise_si_le_solde_couvre_l_inscription(self):
        membre = User.objects.create(username='avec_credit', tolerance_seances_negatives=0)
        MouvementSeance.objects.create(membre=membre, delta=1, motif=MouvementSeance.Motif.ACHAT)

        self.assertTrue(peut_s_inscrire(membre))

    def test_autorise_dans_la_limite_de_la_tolerance_negative(self):
        membre = User.objects.create(username='tolere', tolerance_seances_negatives=2)

        self.assertTrue(peut_s_inscrire(membre))

    def test_refuse_au_dela_de_la_tolerance_negative(self):
        membre = User.objects.create(username='limite_atteinte', tolerance_seances_negatives=2)
        MouvementSeance.objects.create(membre=membre, delta=-2, motif=MouvementSeance.Motif.AJUSTEMENT)

        self.assertFalse(peut_s_inscrire(membre))


class SoldeJokersTests(TestCase):
    def test_membre_sans_mouvement_n_a_pas_de_joker(self):
        membre = User.objects.create(username='sans_joker')

        self.assertEqual(solde_jokers(membre), 0)

    def test_solde_somme_les_mouvements_du_membre(self):
        membre = User.objects.create(username='avec_joker')
        MouvementJoker.objects.create(membre=membre, delta=1, motif=MouvementJoker.Motif.ATTRIBUTION)
        MouvementJoker.objects.create(membre=membre, delta=-1, motif=MouvementJoker.Motif.UTILISATION)
        MouvementJoker.objects.create(membre=membre, delta=1, motif=MouvementJoker.Motif.ATTRIBUTION)

        self.assertEqual(solde_jokers(membre), 1)


class HistoriqueJokersTests(TestCase):
    def test_trie_du_plus_recent_au_plus_ancien(self):
        membre = User.objects.create(username='historique_joker')
        premier = MouvementJoker.objects.create(membre=membre, delta=1, motif=MouvementJoker.Motif.ATTRIBUTION)
        second = MouvementJoker.objects.create(membre=membre, delta=-1, motif=MouvementJoker.Motif.UTILISATION)

        resultat = list(historique_jokers(membre))

        self.assertEqual(resultat, [second, premier])

    def test_ne_contient_pas_les_mouvements_d_un_autre_membre(self):
        membre = User.objects.create(username='historique_joker_a')
        autre = User.objects.create(username='historique_joker_b')
        mouvement = MouvementJoker.objects.create(membre=membre, delta=1, motif=MouvementJoker.Motif.ATTRIBUTION)
        MouvementJoker.objects.create(membre=autre, delta=1, motif=MouvementJoker.Motif.ATTRIBUTION)

        resultat = list(historique_jokers(membre))

        self.assertEqual(resultat, [mouvement])


class AttribuerJokerTests(TestCase):
    def test_attribue_un_joker_au_membre(self):
        coach = User.objects.create(username='coach_attribue')
        membre = User.objects.create(username='beneficiaire')

        attribuer_joker(membre, auteur=coach, commentaire='Geste commercial')

        self.assertEqual(solde_jokers(membre), 1)
        mouvement = MouvementJoker.objects.get(membre=membre)
        self.assertEqual(mouvement.motif, MouvementJoker.Motif.ATTRIBUTION)
        self.assertEqual(mouvement.auteur, coach)
        self.assertEqual(mouvement.commentaire, 'Geste commercial')

    def test_efface_la_date_de_reacquisition(self):
        coach = User.objects.create(username='coach_efface')
        membre = User.objects.create(
            username='avec_echeance', date_reacquisition_joker=timezone.localdate() + datetime.timedelta(days=10)
        )

        attribuer_joker(membre, auteur=coach)

        membre.refresh_from_db()
        self.assertIsNone(membre.date_reacquisition_joker)

    def test_refuse_si_le_membre_a_deja_un_joker(self):
        coach = User.objects.create(username='coach_refuse')
        membre = User.objects.create(username='deja_pourvu')
        MouvementJoker.objects.create(membre=membre, delta=1, motif=MouvementJoker.Motif.ATTRIBUTION)

        with self.assertRaises(ValueError):
            attribuer_joker(membre, auteur=coach)


class RetirerJokerTests(TestCase):
    def test_retire_le_joker_du_membre(self):
        coach = User.objects.create(username='coach_retire')
        membre = User.objects.create(username='a_retirer')
        MouvementJoker.objects.create(membre=membre, delta=1, motif=MouvementJoker.Motif.ATTRIBUTION)

        retirer_joker(membre, auteur=coach, commentaire='Retard répété non justifié')

        self.assertEqual(solde_jokers(membre), 0)
        mouvement = MouvementJoker.objects.filter(delta=-1).get(membre=membre)
        self.assertEqual(mouvement.motif, MouvementJoker.Motif.UTILISATION)
        self.assertEqual(mouvement.auteur, coach)
        self.assertEqual(mouvement.commentaire, 'Retard répété non justifié')

    def test_fixe_la_date_de_reacquisition_a_3_mois(self):
        coach = User.objects.create(username='coach_echeance')
        membre = User.objects.create(username='futur_echeance')
        MouvementJoker.objects.create(membre=membre, delta=1, motif=MouvementJoker.Motif.ATTRIBUTION)

        retirer_joker(membre, auteur=coach)

        membre.refresh_from_db()
        self.assertEqual(membre.date_reacquisition_joker, timezone.localdate() + relativedelta(months=3))

    def test_refuse_si_le_membre_n_a_pas_de_joker(self):
        coach = User.objects.create(username='coach_refuse2')
        membre = User.objects.create(username='sans_joker_a_retirer')

        with self.assertRaises(ValueError):
            retirer_joker(membre, auteur=coach)


class AttribuerJokerInitialTests(TestCase):
    def test_accorde_un_joker_au_nouveau_membre(self):
        membre = User.objects.create(username='nouveau_membre')

        attribuer_joker_initial(membre)

        self.assertEqual(solde_jokers(membre), 1)


class EnregistrerInscriptionTests(TestCase):
    def setUp(self):
        self.coach = User.objects.create(username='coach_test')
        self.membre = User.objects.create(username='membre_test')
        self.seance = Seance.objects.create(
            nom='WOD',
            debut=timezone.now() + datetime.timedelta(days=2),
            duree_minutes=60,
            capacite_max=10,
            delai_annulation_heures=24,
            coach=self.coach,
        )

    def test_enregistrer_inscription_cree_une_inscription_active(self):
        inscription = enregistrer_inscription(membre=self.membre, seance=self.seance, auteur=self.membre)

        self.assertEqual(inscription.statut, Inscription.Statut.INSCRIT)
        self.assertEqual(inscription.membre, self.membre)

    def test_enregistrer_inscription_decompte_une_seance(self):
        MouvementSeance.objects.create(membre=self.membre, delta=5, motif=MouvementSeance.Motif.ACHAT)

        enregistrer_inscription(membre=self.membre, seance=self.seance, auteur=self.membre)

        self.assertEqual(solde_seances(self.membre), 4)

    def test_enregistrer_desinscription_recredite_une_seance(self):
        MouvementSeance.objects.create(membre=self.membre, delta=5, motif=MouvementSeance.Motif.ACHAT)
        inscription = enregistrer_inscription(membre=self.membre, seance=self.seance, auteur=self.membre)

        enregistrer_desinscription(inscription, auteur=self.membre)

        self.assertEqual(solde_seances(self.membre), 5)
        inscription.refresh_from_db()
        self.assertEqual(inscription.statut, Inscription.Statut.DESINSCRIT)


class EnregistrerDesinscriptionTardiveTests(TestCase):
    def setUp(self):
        self.coach = User.objects.create(username='coach_tardif')
        self.membre = User.objects.create(username='membre_tardif')
        self.seance = Seance.objects.create(
            nom='WOD',
            debut=timezone.now() + datetime.timedelta(hours=2),
            duree_minutes=60,
            capacite_max=10,
            delai_annulation_heures=24,
            coach=self.coach,
        )
        MouvementSeance.objects.create(membre=self.membre, delta=5, motif=MouvementSeance.Motif.ACHAT)
        self.inscription = enregistrer_inscription(membre=self.membre, seance=self.seance, auteur=self.membre)

    def test_avec_joker_consomme_le_joker_et_recredite_la_seance(self):
        MouvementJoker.objects.create(membre=self.membre, delta=1, motif=MouvementJoker.Motif.ATTRIBUTION)

        enregistrer_desinscription(self.inscription, auteur=self.membre)

        self.assertEqual(solde_seances(self.membre), 5)
        self.assertEqual(solde_jokers(self.membre), 0)
        self.inscription.refresh_from_db()
        self.assertEqual(self.inscription.statut, Inscription.Statut.DESINSCRIT_TARDIF_JOKER)

    def test_avec_joker_fixe_la_date_de_reacquisition(self):
        MouvementJoker.objects.create(membre=self.membre, delta=1, motif=MouvementJoker.Motif.ATTRIBUTION)

        enregistrer_desinscription(self.inscription, auteur=self.membre)

        self.membre.refresh_from_db()
        self.assertEqual(self.membre.date_reacquisition_joker, timezone.localdate() + relativedelta(months=3))

    def test_sans_joker_ne_recredite_pas_la_seance(self):
        enregistrer_desinscription(self.inscription, auteur=self.membre)

        self.assertEqual(solde_seances(self.membre), 4)
        self.inscription.refresh_from_db()
        self.assertEqual(self.inscription.statut, Inscription.Statut.DESINSCRIT_TARDIF_SANS_JOKER)

    def test_desinscription_normale_ne_touche_pas_aux_jokers(self):
        self.seance.debut = timezone.now() + datetime.timedelta(days=2)
        self.seance.save(update_fields=['debut'])
        MouvementJoker.objects.create(membre=self.membre, delta=1, motif=MouvementJoker.Motif.ATTRIBUTION)

        enregistrer_desinscription(self.inscription, auteur=self.membre)

        self.assertEqual(solde_jokers(self.membre), 1)
        self.assertIsNone(self.membre.date_reacquisition_joker)
        self.inscription.refresh_from_db()
        self.assertEqual(self.inscription.statut, Inscription.Statut.DESINSCRIT)


class MarquerNonPresenteTests(TestCase):
    def setUp(self):
        self.coach = User.objects.create(username='coach_absence')
        self.membre = User.objects.create(username='membre_absent')
        self.seance = Seance.objects.create(
            nom='WOD',
            debut=timezone.now() - datetime.timedelta(hours=1),
            duree_minutes=60,
            capacite_max=10,
            delai_annulation_heures=24,
            coach=self.coach,
        )
        MouvementSeance.objects.create(membre=self.membre, delta=5, motif=MouvementSeance.Motif.ACHAT)
        self.inscription = enregistrer_inscription(membre=self.membre, seance=self.seance, auteur=self.membre)

    def test_marque_le_statut_non_presente(self):
        marquer_non_presente(self.inscription, auteur=self.coach)

        self.inscription.refresh_from_db()
        self.assertEqual(self.inscription.statut, Inscription.Statut.NON_PRESENTE)

    def test_consomme_le_joker_si_disponible(self):
        MouvementJoker.objects.create(membre=self.membre, delta=1, motif=MouvementJoker.Motif.ATTRIBUTION)

        marquer_non_presente(self.inscription, auteur=self.coach, commentaire='Absent sans prévenir')

        self.assertEqual(solde_jokers(self.membre), 0)
        mouvement = MouvementJoker.objects.filter(delta=-1).get(membre=self.membre)
        self.assertEqual(mouvement.inscription, self.inscription)
        self.assertEqual(mouvement.commentaire, 'Absent sans prévenir')
        self.membre.refresh_from_db()
        self.assertEqual(self.membre.date_reacquisition_joker, timezone.localdate() + relativedelta(months=3))

    def test_ne_consomme_rien_si_pas_de_joker_disponible(self):
        marquer_non_presente(self.inscription, auteur=self.coach)

        self.assertEqual(solde_jokers(self.membre), 0)
        self.assertFalse(MouvementJoker.objects.filter(membre=self.membre).exists())

    def test_ne_touche_pas_au_solde_de_seances(self):
        marquer_non_presente(self.inscription, auteur=self.coach)

        self.assertEqual(solde_seances(self.membre), 4)

    def test_trace_la_seance_due_meme_sans_joker(self):
        marquer_non_presente(self.inscription, auteur=self.coach)

        mouvement = MouvementSeance.objects.get(
            membre=self.membre, motif=MouvementSeance.Motif.NON_PRESENTATION
        )
        self.assertEqual(mouvement.delta, 0)
        self.assertEqual(mouvement.inscription, self.inscription)
        self.assertEqual(mouvement.auteur, self.coach)

    def test_trace_aussi_la_non_presentation_quand_un_joker_est_consomme(self):
        MouvementJoker.objects.create(membre=self.membre, delta=1, motif=MouvementJoker.Motif.ATTRIBUTION)

        marquer_non_presente(self.inscription, auteur=self.coach)

        self.assertTrue(
            MouvementSeance.objects.filter(
                membre=self.membre, motif=MouvementSeance.Motif.NON_PRESENTATION
            ).exists()
        )


class PromouvoirListeAttenteTests(TestCase):
    def setUp(self):
        self.coach = User.objects.create(username='coach_promo')
        self.seance = Seance.objects.create(
            nom='WOD',
            debut=timezone.now() + datetime.timedelta(hours=48),
            duree_minutes=60,
            capacite_max=1,
            delai_annulation_heures=24,
            coach=self.coach,
        )

    def test_promeut_le_premier_de_la_liste_si_place_et_plus_de_24h(self):
        membre = User.objects.create(username='attente1')
        MouvementSeance.objects.create(membre=membre, delta=5, motif=MouvementSeance.Motif.ACHAT)
        attente = Inscription.objects.create(
            membre=membre, seance=self.seance, auteur=membre, statut=Inscription.Statut.EN_ATTENTE
        )

        promu = promouvoir_liste_attente(self.seance)

        attente.refresh_from_db()
        self.assertEqual(promu, attente)
        self.assertEqual(attente.statut, Inscription.Statut.INSCRIT)
        self.assertEqual(solde_seances(membre), 4)

    def test_ne_promeut_pas_si_la_seance_est_dans_moins_de_24h(self):
        self.seance.debut = timezone.now() + datetime.timedelta(hours=2)
        self.seance.save(update_fields=['debut'])
        membre = User.objects.create(username='attente2')
        MouvementSeance.objects.create(membre=membre, delta=5, motif=MouvementSeance.Motif.ACHAT)
        attente = Inscription.objects.create(
            membre=membre, seance=self.seance, auteur=membre, statut=Inscription.Statut.EN_ATTENTE
        )

        promu = promouvoir_liste_attente(self.seance)

        attente.refresh_from_db()
        self.assertIsNone(promu)
        self.assertEqual(attente.statut, Inscription.Statut.EN_ATTENTE)

    def test_ne_promeut_pas_si_aucune_place_restante(self):
        occupant = User.objects.create(username='occupant')
        Inscription.objects.create(membre=occupant, seance=self.seance, auteur=occupant)
        membre = User.objects.create(username='attente3')
        MouvementSeance.objects.create(membre=membre, delta=5, motif=MouvementSeance.Motif.ACHAT)
        attente = Inscription.objects.create(
            membre=membre, seance=self.seance, auteur=membre, statut=Inscription.Statut.EN_ATTENTE
        )

        promu = promouvoir_liste_attente(self.seance)

        attente.refresh_from_db()
        self.assertIsNone(promu)
        self.assertEqual(attente.statut, Inscription.Statut.EN_ATTENTE)

    def test_passe_au_suivant_si_le_premier_n_a_pas_assez_de_solde(self):
        inelig = User.objects.create(username='inelig', tolerance_seances_negatives=0)
        elig = User.objects.create(username='elig')
        MouvementSeance.objects.create(membre=elig, delta=5, motif=MouvementSeance.Motif.ACHAT)
        attente_inelig = Inscription.objects.create(
            membre=inelig, seance=self.seance, auteur=inelig, statut=Inscription.Statut.EN_ATTENTE
        )
        attente_elig = Inscription.objects.create(
            membre=elig, seance=self.seance, auteur=elig, statut=Inscription.Statut.EN_ATTENTE
        )

        promu = promouvoir_liste_attente(self.seance)

        attente_inelig.refresh_from_db()
        attente_elig.refresh_from_db()
        self.assertEqual(promu, attente_elig)
        self.assertEqual(attente_inelig.statut, Inscription.Statut.EN_ATTENTE)
        self.assertEqual(attente_elig.statut, Inscription.Statut.INSCRIT)


class EnregistrerDesinscriptionPromotionTests(TestCase):
    def setUp(self):
        self.coach = User.objects.create(username='coach_desinscription_promo')
        self.seance = Seance.objects.create(
            nom='WOD',
            debut=timezone.now() + datetime.timedelta(hours=48),
            duree_minutes=60,
            capacite_max=1,
            delai_annulation_heures=24,
            coach=self.coach,
        )
        self.inscrit = User.objects.create(username='inscrit_promo')
        MouvementSeance.objects.create(membre=self.inscrit, delta=5, motif=MouvementSeance.Motif.ACHAT)
        self.inscription = enregistrer_inscription(membre=self.inscrit, seance=self.seance, auteur=self.inscrit)

        self.attendant = User.objects.create(username='attendant_promo')
        MouvementSeance.objects.create(membre=self.attendant, delta=5, motif=MouvementSeance.Motif.ACHAT)
        self.attente = Inscription.objects.create(
            membre=self.attendant, seance=self.seance, auteur=self.attendant, statut=Inscription.Statut.EN_ATTENTE
        )

    def test_desinscription_promeut_automatiquement_le_premier_de_la_liste(self):
        enregistrer_desinscription(self.inscription, auteur=self.inscrit)

        self.attente.refresh_from_db()
        self.assertEqual(self.attente.statut, Inscription.Statut.INSCRIT)
        self.assertEqual(solde_seances(self.attendant), 4)

    def test_desinscription_ne_promeut_pas_si_la_seance_est_dans_moins_de_24h(self):
        self.seance.debut = timezone.now() + datetime.timedelta(hours=2)
        self.seance.save(update_fields=['debut'])

        enregistrer_desinscription(self.inscription, auteur=self.inscrit)

        self.attente.refresh_from_db()
        self.assertEqual(self.attente.statut, Inscription.Statut.EN_ATTENTE)


class MarquerNonPresenteVueTests(TestCase):
    def setUp(self):
        self.coach = User.objects.create_user(
            username='coach_vue_absence', password='motdepasse123', role=User.Role.GESTIONNAIRE
        )
        self.membre = User.objects.create(username='membre_vue_absence')
        self.seance = Seance.objects.create(
            nom='WOD',
            debut=timezone.now() - datetime.timedelta(hours=1),
            duree_minutes=60,
            capacite_max=10,
            delai_annulation_heures=24,
            coach=self.coach,
        )
        MouvementSeance.objects.create(membre=self.membre, delta=5, motif=MouvementSeance.Motif.ACHAT)
        self.inscription = enregistrer_inscription(membre=self.membre, seance=self.seance, auteur=self.membre)

    def test_un_coach_peut_marquer_une_absence(self):
        self.client.force_login(self.coach)

        self.client.post(
            reverse('bookings:marquer_non_presente', args=[self.seance.pk, self.membre.pk]),
            {'commentaire': 'Absent sans prévenir'},
        )

        self.inscription.refresh_from_db()
        self.assertEqual(self.inscription.statut, Inscription.Statut.NON_PRESENTE)

    def test_un_membre_ne_peut_pas_marquer_une_absence(self):
        self.client.force_login(self.membre)

        response = self.client.post(
            reverse('bookings:marquer_non_presente', args=[self.seance.pk, self.membre.pk])
        )

        self.assertEqual(response.status_code, 403)

    def test_un_coach_simple_peut_marquer_une_absence(self):
        coach_simple = User.objects.create_user(
            username='coach_simple_absence', password='motdepasse123', role=User.Role.COACH
        )
        self.client.force_login(coach_simple)

        self.client.post(
            reverse('bookings:marquer_non_presente', args=[self.seance.pk, self.membre.pk])
        )

        self.inscription.refresh_from_db()
        self.assertEqual(self.inscription.statut, Inscription.Statut.NON_PRESENTE)

    def test_refuse_si_la_seance_n_est_pas_encore_passee(self):
        self.seance.debut = timezone.now() + datetime.timedelta(hours=1)
        self.seance.save(update_fields=['debut'])
        self.client.force_login(self.coach)

        self.client.post(reverse('bookings:marquer_non_presente', args=[self.seance.pk, self.membre.pk]))

        self.inscription.refresh_from_db()
        self.assertEqual(self.inscription.statut, Inscription.Statut.INSCRIT)

    def test_un_coach_simple_ne_peut_pas_desinscrire_un_membre(self):
        coach_simple = User.objects.create_user(
            username='coach_simple_desinscrire', password='motdepasse123', role=User.Role.COACH
        )
        self.seance.debut = timezone.now() + datetime.timedelta(days=1)
        self.seance.save(update_fields=['debut'])
        self.client.force_login(coach_simple)

        response = self.client.post(
            reverse('bookings:desinscrire_membre', args=[self.seance.pk, self.membre.pk])
        )

        self.assertEqual(response.status_code, 403)


class JokerVueTests(TestCase):
    def setUp(self):
        self.coach = User.objects.create_user(
            username='coach_vue_joker', password='motdepasse123', role=User.Role.GESTIONNAIRE
        )
        self.membre = User.objects.create(username='membre_vue_joker')

    def test_un_coach_peut_attribuer_un_joker(self):
        self.client.force_login(self.coach)

        self.client.post(reverse('bookings:attribuer_joker', args=[self.membre.pk]), {'commentaire': 'Geste'})

        self.assertEqual(solde_jokers(self.membre), 1)

    def test_un_membre_ne_peut_pas_attribuer_de_joker(self):
        self.client.force_login(self.membre)

        response = self.client.post(reverse('bookings:attribuer_joker', args=[self.membre.pk]))

        self.assertEqual(response.status_code, 403)

    def test_un_coach_simple_ne_peut_pas_attribuer_de_joker(self):
        coach_simple = User.objects.create_user(
            username='coach_simple_joker', password='motdepasse123', role=User.Role.COACH
        )
        self.client.force_login(coach_simple)

        response = self.client.post(reverse('bookings:attribuer_joker', args=[self.membre.pk]))

        self.assertEqual(response.status_code, 403)

    def test_un_coach_peut_retirer_un_joker(self):
        MouvementJoker.objects.create(membre=self.membre, delta=1, motif=MouvementJoker.Motif.ATTRIBUTION)
        self.client.force_login(self.coach)

        self.client.post(reverse('bookings:retirer_joker', args=[self.membre.pk]), {'commentaire': 'Motif'})

        self.assertEqual(solde_jokers(self.membre), 0)


class NotifierCoachSeancePleineTests(TestCase):
    def setUp(self):
        self.coach = User.objects.create(username='coach_pleine', role=User.Role.COACH)
        self.membre = User.objects.create_user(username='membre_pleine', password='motdepasse123')
        MouvementSeance.objects.create(membre=self.membre, delta=5, motif=MouvementSeance.Motif.ACHAT)
        self.seance = Seance.objects.create(
            nom='WOD',
            debut=timezone.now() + datetime.timedelta(days=2),
            duree_minutes=60,
            capacite_max=1,
            delai_annulation_heures=24,
            coach=self.coach,
        )

    @patch('apps.bookings.views.notifier_evenement_seance')
    def test_notifie_l_evenement_seance_complete_quand_la_seance_devient_pleine(self, mock_notifier):
        self.client.force_login(self.membre)

        self.client.post(reverse('bookings:inscrire', args=[self.seance.pk]))

        champs_notifies = [call.args[2] for call in mock_notifier.call_args_list]
        self.assertIn('notifie_seance_complete', champs_notifies)

    @patch('apps.bookings.views.notifier_evenement_seance')
    def test_ne_notifie_pas_seance_complete_si_la_seance_n_est_pas_pleine(self, mock_notifier):
        self.seance.capacite_max = 10
        self.seance.save(update_fields=['capacite_max'])
        self.client.force_login(self.membre)

        self.client.post(reverse('bookings:inscrire', args=[self.seance.pk]))

        champs_notifies = [call.args[2] for call in mock_notifier.call_args_list]
        self.assertNotIn('notifie_seance_complete', champs_notifies)
        self.assertIn('notifie_inscription', champs_notifies)


class EnregistrerDesinscriptionNotifieCoachTests(TestCase):
    def setUp(self):
        self.coach = User.objects.create(username='coach_desinscr_notif', role=User.Role.COACH)
        self.membre = User.objects.create(username='membre_desinscr_notif')
        MouvementSeance.objects.create(membre=self.membre, delta=5, motif=MouvementSeance.Motif.ACHAT)
        self.seance = Seance.objects.create(
            nom='WOD',
            debut=timezone.now() + datetime.timedelta(days=2),
            duree_minutes=60,
            capacite_max=10,
            delai_annulation_heures=24,
            coach=self.coach,
        )
        self.inscription = enregistrer_inscription(membre=self.membre, seance=self.seance, auteur=self.membre)

    @patch('apps.bookings.services.notifier_evenement_seance')
    def test_notifie_l_evenement_desinscription_quand_un_membre_se_desinscrit(self, mock_notifier):
        enregistrer_desinscription(self.inscription, auteur=self.membre)

        mock_notifier.assert_called_once()
        seance_appelee, message, champ = mock_notifier.call_args.args
        self.assertEqual(seance_appelee, self.seance)
        self.assertEqual(champ, 'notifie_desinscription')
        self.assertIn(str(self.membre), message)


class InscrireViewMessageOuvertureTests(TestCase):
    def test_le_message_indique_la_date_et_l_heure_d_ouverture(self):
        membre = User.objects.create_user(username='membre_avant_ouverture', password='motdepasse123')
        seance = Seance.objects.create(
            nom='WOD',
            debut=timezone.now() + datetime.timedelta(days=20),
            duree_minutes=60,
            capacite_max=10,
            delai_annulation_heures=24,
        )
        self.client.force_login(membre)

        response = self.client.post(reverse('bookings:inscrire', args=[seance.pk]), follow=True)

        messages = [str(m) for m in response.context['messages']]
        self.assertTrue(any('21:00' in message for message in messages), messages)


MAINTENANT = timezone.make_aware(datetime.datetime(2026, 10, 7, 10, 0))  # un mercredi, 10h00


class PermutationTestCase(TestCase):
    """Fige l'heure à mercredi 7 octobre 2026, 10h00, pour éviter tout aléa autour de minuit."""

    def setUp(self):
        patcher = patch('django.utils.timezone.now', return_value=MAINTENANT)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.coach = User.objects.create(username='coach_permutation')
        self.membre = User.objects.create_user(username='membre_permutation', password='motdepasse123')
        MouvementSeance.objects.create(membre=self.membre, delta=5, motif=MouvementSeance.Motif.ACHAT)

    def seance(self, heure=12, jour=7, capacite=10, nom='WOD'):
        return Seance.objects.create(
            nom=nom,
            debut=timezone.make_aware(datetime.datetime(2026, 10, jour, heure, 0)),
            capacite_max=capacite,
            delai_annulation_heures=24,
            coach=self.coach,
        )

    def inscrire(self, seance, membre=None):
        membre = membre or self.membre
        return enregistrer_inscription(membre=membre, seance=seance, auteur=membre)


class SeancesPermutablesTests(PermutationTestCase):
    def test_liste_les_autres_seances_du_jour_avec_des_places(self):
        origine = self.seance(heure=12)
        cible = self.seance(heure=18, nom='Cible')
        self.inscrire(origine)

        self.assertEqual(seances_permutables(self.membre, origine), [cible])

    def test_exclut_les_seances_completes(self):
        origine = self.seance(heure=12)
        pleine = self.seance(heure=18, capacite=1)
        self.inscrire(origine)
        self.inscrire(pleine, membre=User.objects.create(username='occupant'))

        self.assertEqual(seances_permutables(self.membre, origine), [])

    def test_exclut_les_seances_deja_commencees(self):
        origine = self.seance(heure=12)
        self.seance(heure=9)  # il est 10h00
        self.inscrire(origine)

        self.assertEqual(seances_permutables(self.membre, origine), [])

    def test_exclut_les_seances_d_un_autre_jour(self):
        origine = self.seance(heure=12)
        self.seance(heure=18, jour=8)
        self.inscrire(origine)

        self.assertEqual(seances_permutables(self.membre, origine), [])

    def test_exclut_les_seances_ou_le_membre_est_deja_inscrit_ou_en_attente(self):
        origine = self.seance(heure=12)
        deja_inscrit = self.seance(heure=18)
        en_attente = self.seance(heure=19)
        self.inscrire(origine)
        self.inscrire(deja_inscrit)
        Inscription.objects.create(membre=self.membre, seance=en_attente, statut=Inscription.Statut.EN_ATTENTE)

        self.assertEqual(seances_permutables(self.membre, origine), [])

    def test_vide_si_la_seance_d_origine_n_est_pas_aujourd_hui(self):
        origine = self.seance(heure=12, jour=8)
        self.seance(heure=18, jour=8)
        self.inscrire(origine)

        self.assertEqual(seances_permutables(self.membre, origine), [])

    def test_vide_si_le_membre_n_est_pas_inscrit(self):
        origine = self.seance(heure=12)
        self.seance(heure=18)

        self.assertEqual(seances_permutables(self.membre, origine), [])


class PermuterInscriptionTests(PermutationTestCase):
    def setUp(self):
        super().setUp()
        self.origine = self.seance(heure=12)  # dans 2h : désinscription tardive
        self.cible = self.seance(heure=18, nom='Cible')
        self.inscription = self.inscrire(self.origine)

    def test_inscrit_le_membre_sur_la_nouvelle_seance_et_libere_l_ancienne(self):
        permuter_inscription(self.inscription, self.cible, auteur=self.membre)

        self.assertTrue(
            Inscription.objects.filter(membre=self.membre, seance=self.cible, statut=Inscription.Statut.INSCRIT).exists()
        )
        self.inscription.refresh_from_db()
        self.assertEqual(self.inscription.statut, Inscription.Statut.PERMUTE)
        self.assertEqual(self.origine.places_restantes, 10)
        self.assertEqual(self.cible.places_restantes, 9)

    def test_le_solde_de_seances_est_inchange(self):
        permuter_inscription(self.inscription, self.cible, auteur=self.membre)

        self.assertEqual(solde_seances(self.membre), 4)

    def test_le_solde_est_inchange_meme_a_la_limite_de_la_tolerance(self):
        MouvementSeance.objects.create(membre=self.membre, delta=-4, motif=MouvementSeance.Motif.AJUSTEMENT)

        permuter_inscription(self.inscription, self.cible, auteur=self.membre)

        self.assertEqual(solde_seances(self.membre), 0)

    def test_le_joker_n_est_pas_consomme_meme_en_permutation_tardive(self):
        MouvementJoker.objects.create(membre=self.membre, delta=1, motif=MouvementJoker.Motif.ATTRIBUTION)
        self.assertTrue(self.origine.desinscription_tardive)

        permuter_inscription(self.inscription, self.cible, auteur=self.membre)

        self.assertEqual(solde_jokers(self.membre), 1)
        self.membre.refresh_from_db()
        self.assertIsNone(self.membre.date_reacquisition_joker)

    def test_trace_un_mouvement_de_permutation_sur_l_ancienne_seance(self):
        permuter_inscription(self.inscription, self.cible, auteur=self.membre)

        mouvement = MouvementSeance.objects.get(motif=MouvementSeance.Motif.PERMUTATION)
        self.assertEqual((mouvement.membre, mouvement.delta, mouvement.inscription), (self.membre, 1, self.inscription))
        self.assertIn('Permutation', mouvement.libelle)
        self.assertIn('07/10/2026 12:00', mouvement.libelle)

    def test_refuse_une_seance_non_permutable(self):
        autre_jour = self.seance(heure=18, jour=8)

        with self.assertRaises(ValueError):
            permuter_inscription(self.inscription, autre_jour, auteur=self.membre)

        self.inscription.refresh_from_db()
        self.assertEqual(self.inscription.statut, Inscription.Statut.INSCRIT)
        self.assertEqual(solde_seances(self.membre), 4)

    def test_refuse_si_l_inscription_n_est_plus_active(self):
        self.inscription.statut = Inscription.Statut.DESINSCRIT
        self.inscription.save(update_fields=['statut'])

        with self.assertRaises(ValueError):
            permuter_inscription(self.inscription, self.cible, auteur=self.membre)


class PermuterViewTests(PermutationTestCase):
    def setUp(self):
        super().setUp()
        self.origine = self.seance(heure=12)
        self.cible = self.seance(heure=18, nom='Cible')
        self.inscription = self.inscrire(self.origine)
        self.client.force_login(self.membre)

    def _post(self, vers):
        return self.client.post(reverse('bookings:permuter', args=[self.origine.pk]), {'vers': vers})

    def test_permute_et_redirige_vers_la_nouvelle_seance(self):
        response = self._post(self.cible.pk)

        self.assertRedirects(response, reverse('scheduling:seance_detail', args=[self.cible.pk]))
        self.assertTrue(
            Inscription.objects.filter(membre=self.membre, seance=self.cible, statut=Inscription.Statut.INSCRIT).exists()
        )

    def test_refuse_une_cible_non_permutable_sans_rien_modifier(self):
        autre_jour = self.seance(heure=18, jour=8)

        self._post(autre_jour.pk)

        self.inscription.refresh_from_db()
        self.assertEqual(self.inscription.statut, Inscription.Statut.INSCRIT)

    def test_refuse_si_le_membre_n_est_pas_inscrit_a_la_seance_d_origine(self):
        autre = User.objects.create_user(username='autre_permutation', password='motdepasse123')
        self.client.force_login(autre)

        self._post(self.cible.pk)

        self.assertFalse(Inscription.objects.filter(membre=autre).exists())

    def test_refuse_une_requete_get(self):
        response = self.client.get(reverse('bookings:permuter', args=[self.origine.pk]))

        self.assertEqual(response.status_code, 405)

    def test_la_fiche_seance_propose_la_permutation(self):
        response = self.client.get(reverse('scheduling:seance_detail', args=[self.origine.pk]))

        self.assertContains(response, 'Permuter')
        self.assertContains(response, 'Cible')

    def test_pas_de_bouton_si_aucune_autre_seance_n_a_de_place(self):
        self.cible.capacite_max = 1
        self.cible.save(update_fields=['capacite_max'])
        self.inscrire(self.cible, membre=User.objects.create(username='occupant_vue'))

        response = self.client.get(reverse('scheduling:seance_detail', args=[self.origine.pk]))

        self.assertNotContains(response, 'Permuter')

    def test_pas_de_bouton_si_le_membre_n_est_pas_inscrit(self):
        autre = User.objects.create_user(username='non_inscrit_permutation', password='motdepasse123')
        self.client.force_login(autre)

        response = self.client.get(reverse('scheduling:seance_detail', args=[self.origine.pk]))

        self.assertNotContains(response, 'Permuter')

    def test_pas_de_bouton_si_la_seance_n_est_pas_aujourd_hui(self):
        demain = self.seance(heure=12, jour=8, nom='Demain')
        self.seance(heure=18, jour=8, nom='Demain soir')
        self.inscrire(demain)

        response = self.client.get(reverse('scheduling:seance_detail', args=[demain.pk]))

        self.assertNotContains(response, 'Permuter')
