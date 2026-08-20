import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.purchases.models import MouvementSeance
from apps.purchases.services import solde_seances
from apps.scheduling.models import Seance

from .models import Inscription
from .services import enregistrer_desinscription, enregistrer_inscription, peut_s_inscrire

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
