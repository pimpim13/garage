import datetime

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
    promouvoir_liste_attente,
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
