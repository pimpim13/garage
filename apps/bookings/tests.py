import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.purchases.models import MouvementSeance
from apps.purchases.services import solde_seances
from apps.scheduling.models import Seance

from .models import Inscription
from .services import (
    enregistrer_desinscription,
    enregistrer_inscription,
    peut_s_inscrire,
    promouvoir_liste_attente,
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


class EnregistrerInscriptionTests(TestCase):
    def setUp(self):
        self.coach = User.objects.create(username='coach_test')
        self.membre = User.objects.create(username='membre_test')
        self.seance = Seance.objects.create(
            nom='WOD',
            debut=timezone.now() + datetime.timedelta(days=1),
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
