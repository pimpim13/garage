import datetime

from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Famille
from apps.offers.models import Offre

from .models import Achat, MouvementSeance
from .services import ajuster_solde, enregistrer_achat, historique_seances, solde_seances, statut_solde

User = get_user_model()


class SoldeSeancesTests(TestCase):
    def test_membre_sans_mouvement_a_un_solde_nul(self):
        membre = User.objects.create(username='sansmouvement')

        self.assertEqual(solde_seances(membre), 0)

    def test_solde_somme_les_mouvements_du_membre(self):
        membre = User.objects.create(username='avecmouvements')
        MouvementSeance.objects.create(membre=membre, delta=11, motif=MouvementSeance.Motif.ACHAT)
        MouvementSeance.objects.create(membre=membre, delta=-1, motif=MouvementSeance.Motif.INSCRIPTION)

        self.assertEqual(solde_seances(membre), 10)

    def test_membre_en_famille_partage_le_solde_de_tous_les_membres_lies(self):
        famille = Famille.objects.create(nom='Dupont')
        parent = User.objects.create(username='parent_dupont', famille=famille)
        enfant = User.objects.create(username='enfant_dupont', famille=famille)
        MouvementSeance.objects.create(membre=parent, delta=11, motif=MouvementSeance.Motif.ACHAT)
        MouvementSeance.objects.create(membre=enfant, delta=-1, motif=MouvementSeance.Motif.INSCRIPTION)

        self.assertEqual(solde_seances(parent), 10)
        self.assertEqual(solde_seances(enfant), 10)

    def test_solde_nul_si_date_expiration_depassee(self):
        hier = timezone.localdate() - datetime.timedelta(days=1)
        membre = User.objects.create(username='perime', date_expiration_solde=hier)
        MouvementSeance.objects.create(membre=membre, delta=11, motif=MouvementSeance.Motif.ACHAT)

        self.assertEqual(solde_seances(membre), 0)


class EnregistrerAchatTests(TestCase):
    def setUp(self):
        self.offre = Offre.objects.create(
            nom='Carnet 11 séances',
            type_offre=Offre.TypeOffre.CARNET,
            prix=100,
            nombre_seances=11,
        )
        self.gestionnaire = User.objects.create(username='gestionnaire_test')

    def test_enregistrer_achat_credite_le_solde(self):
        membre = User.objects.create(username='acheteur')

        enregistrer_achat(membre=membre, offre=self.offre, prix_paye=100, saisi_par=self.gestionnaire)

        self.assertEqual(solde_seances(membre), 11)

    def test_enregistrer_achat_cree_un_achat_paye(self):
        membre = User.objects.create(username='acheteur2')

        enregistrer_achat(membre=membre, offre=self.offre, prix_paye=100, saisi_par=self.gestionnaire)

        achat = Achat.objects.get(membre=membre)
        self.assertEqual(achat.statut_paiement, Achat.StatutPaiement.PAYE)
        self.assertEqual(achat.nombre_seances, 11)
        self.assertEqual(achat.saisi_par, self.gestionnaire)

    def test_premier_achat_fixe_expiration_a_6_mois(self):
        membre = User.objects.create(username='premier_achat')
        aujourdhui = timezone.localdate()

        enregistrer_achat(membre=membre, offre=self.offre, prix_paye=100, saisi_par=self.gestionnaire)

        membre.refresh_from_db()
        annee, mois = aujourdhui.year, aujourdhui.month + 6
        if mois > 12:
            annee, mois = annee + 1, mois - 12
        self.assertEqual(membre.date_expiration_solde, aujourdhui.replace(year=annee, month=mois))

    def test_achat_sur_pool_familial_prolonge_expiration_de_la_famille(self):
        famille = Famille.objects.create(nom='Martin')
        membre = User.objects.create(username='membre_famille_achat', famille=famille)

        enregistrer_achat(membre=membre, offre=self.offre, prix_paye=100, saisi_par=self.gestionnaire)

        famille.refresh_from_db()
        membre.refresh_from_db()
        self.assertIsNotNone(famille.date_expiration_solde)
        self.assertIsNone(membre.date_expiration_solde)

    def test_second_achat_prolonge_depuis_expiration_existante_pas_depuis_aujourdhui(self):
        dans_5_mois = timezone.localdate() + relativedelta(months=5)
        membre = User.objects.create(username='deja_actif', date_expiration_solde=dans_5_mois)

        enregistrer_achat(membre=membre, offre=self.offre, prix_paye=100, saisi_par=self.gestionnaire)

        membre.refresh_from_db()
        self.assertEqual(membre.date_expiration_solde, dans_5_mois + relativedelta(months=6))


class StatutSoldeTests(TestCase):
    def test_solde_positif_est_vert(self):
        membre = User.objects.create(username='positif', tolerance_seances_negatives=2)
        MouvementSeance.objects.create(membre=membre, delta=1, motif=MouvementSeance.Motif.ACHAT)

        self.assertEqual(statut_solde(membre), 'vert')

    def test_solde_nul_est_orange(self):
        membre = User.objects.create(username='nul', tolerance_seances_negatives=2)

        self.assertEqual(statut_solde(membre), 'orange')

    def test_solde_negatif_sous_la_tolerance_est_orange(self):
        membre = User.objects.create(username='entame', tolerance_seances_negatives=2)
        MouvementSeance.objects.create(membre=membre, delta=-1, motif=MouvementSeance.Motif.AJUSTEMENT)

        self.assertEqual(statut_solde(membre), 'orange')

    def test_solde_a_la_tolerance_est_rouge(self):
        membre = User.objects.create(username='limite', tolerance_seances_negatives=2)
        MouvementSeance.objects.create(membre=membre, delta=-2, motif=MouvementSeance.Motif.AJUSTEMENT)

        self.assertEqual(statut_solde(membre), 'rouge')


class AjusterSoldeTests(TestCase):
    def test_ajuster_solde_credite_le_membre(self):
        membre = User.objects.create(username='a_crediter')
        gestionnaire = User.objects.create(username='gestionnaire_ajust')

        ajuster_solde(membre=membre, delta=10, auteur=gestionnaire)

        self.assertEqual(solde_seances(membre), 10)

    def test_ajuster_solde_cree_un_mouvement_ajustement_trace(self):
        membre = User.objects.create(username='a_tracer')
        gestionnaire = User.objects.create(username='gestionnaire_trace')

        ajuster_solde(membre=membre, delta=-1, auteur=gestionnaire)

        mouvement = MouvementSeance.objects.get(membre=membre)
        self.assertEqual(mouvement.delta, -1)
        self.assertEqual(mouvement.motif, MouvementSeance.Motif.AJUSTEMENT)
        self.assertEqual(mouvement.auteur, gestionnaire)


class HistoriqueSeancesTests(TestCase):
    def test_historique_trie_du_plus_recent_au_plus_ancien(self):
        membre = User.objects.create(username='historique')
        premier = MouvementSeance.objects.create(membre=membre, delta=11, motif=MouvementSeance.Motif.ACHAT)
        second = MouvementSeance.objects.create(membre=membre, delta=-1, motif=MouvementSeance.Motif.INSCRIPTION)

        resultat = list(historique_seances(membre))

        self.assertEqual(resultat, [second, premier])

    def test_historique_inclut_les_mouvements_de_toute_la_famille(self):
        famille = Famille.objects.create(nom='Bernard')
        parent = User.objects.create(username='parent_bernard', famille=famille)
        enfant = User.objects.create(username='enfant_bernard', famille=famille)
        mouvement_parent = MouvementSeance.objects.create(
            membre=parent, delta=11, motif=MouvementSeance.Motif.ACHAT
        )
        mouvement_enfant = MouvementSeance.objects.create(
            membre=enfant, delta=-1, motif=MouvementSeance.Motif.INSCRIPTION
        )

        resultat = set(historique_seances(parent))

        self.assertEqual(resultat, {mouvement_parent, mouvement_enfant})
