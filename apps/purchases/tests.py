import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Famille

from .models import MouvementSeance
from .services import solde_seances

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
