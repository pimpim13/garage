import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.bookings.models import Inscription
from apps.scheduling.models import Seance

from . import services


def creer_seance(nom='WOD', jours=-3, heure=18, capacite=10, coach=None):
    jour = timezone.localdate() + datetime.timedelta(days=jours)
    debut = timezone.make_aware(datetime.datetime.combine(jour, datetime.time(heure, 0)))
    return Seance.objects.create(nom=nom, debut=debut, capacite_max=capacite, coach=coach)


def inscrire(seance, nombre, statut=Inscription.Statut.INSCRIT):
    for i in range(nombre):
        membre = User.objects.create_user(username=f'm{seance.pk}_{statut}_{i}_{Inscription.objects.count()}')
        Inscription.objects.create(membre=membre, seance=seance, statut=statut)


def filtres_larges(**kwargs):
    aujourd_hui = timezone.localdate()
    kwargs.setdefault('debut', aujourd_hui - datetime.timedelta(days=60))
    kwargs.setdefault('fin', aujourd_hui)
    return services.Filtres(**kwargs)


class ResoudrePeriodeTests(TestCase):
    aujourd_hui = datetime.date(2026, 10, 14)  # mercredi

    def test_semaine_va_du_lundi_au_dimanche(self):
        debut, fin = services.resoudre_periode('semaine', '', '', self.aujourd_hui)
        self.assertEqual((debut, fin), (datetime.date(2026, 10, 12), datetime.date(2026, 10, 18)))

    def test_mois(self):
        debut, fin = services.resoudre_periode('mois', '', '', self.aujourd_hui)
        self.assertEqual((debut, fin), (datetime.date(2026, 10, 1), datetime.date(2026, 10, 31)))

    def test_trimestre(self):
        debut, fin = services.resoudre_periode('trimestre', '', '', self.aujourd_hui)
        self.assertEqual((debut, fin), (datetime.date(2026, 10, 1), datetime.date(2026, 12, 31)))

    def test_annee(self):
        debut, fin = services.resoudre_periode('annee', '', '', self.aujourd_hui)
        self.assertEqual((debut, fin), (datetime.date(2026, 1, 1), datetime.date(2026, 12, 31)))

    def test_personnalisee(self):
        debut, fin = services.resoudre_periode('perso', '2026-09-01', '2026-09-15', self.aujourd_hui)
        self.assertEqual((debut, fin), (datetime.date(2026, 9, 1), datetime.date(2026, 9, 15)))

    def test_personnalisee_invalide_retombe_sur_le_mois(self):
        debut, fin = services.resoudre_periode('perso', 'abc', '', self.aujourd_hui)
        self.assertEqual((debut, fin), (datetime.date(2026, 10, 1), datetime.date(2026, 10, 31)))

    def test_personnalisee_inversee_est_remise_dans_l_ordre(self):
        debut, fin = services.resoudre_periode('perso', '2026-09-15', '2026-09-01', self.aujourd_hui)
        self.assertEqual((debut, fin), (datetime.date(2026, 9, 1), datetime.date(2026, 9, 15)))

    def test_preset_inconnu_retombe_sur_le_mois(self):
        debut, fin = services.resoudre_periode('???', '', '', self.aujourd_hui)
        self.assertEqual((debut, fin), (datetime.date(2026, 10, 1), datetime.date(2026, 10, 31)))


class PeriodeVoisineTests(TestCase):
    def test_semaine_precedente_et_suivante(self):
        debut, fin = datetime.date(2026, 10, 12), datetime.date(2026, 10, 18)

        self.assertEqual(
            services.periode_voisine('semaine', debut, fin, -1),
            (datetime.date(2026, 10, 5), datetime.date(2026, 10, 11)),
        )
        self.assertEqual(
            services.periode_voisine('semaine', debut, fin, 1),
            (datetime.date(2026, 10, 19), datetime.date(2026, 10, 25)),
        )

    def test_mois_precedent_a_cheval_sur_l_annee(self):
        debut, fin = datetime.date(2027, 1, 1), datetime.date(2027, 1, 31)

        self.assertEqual(
            services.periode_voisine('mois', debut, fin, -1),
            (datetime.date(2026, 12, 1), datetime.date(2026, 12, 31)),
        )

    def test_mois_suivant_gere_les_mois_courts(self):
        debut, fin = datetime.date(2027, 1, 1), datetime.date(2027, 1, 31)

        self.assertEqual(
            services.periode_voisine('mois', debut, fin, 1),
            (datetime.date(2027, 2, 1), datetime.date(2027, 2, 28)),
        )

    def test_trimestre_et_annee(self):
        self.assertEqual(
            services.periode_voisine('trimestre', datetime.date(2026, 10, 1), datetime.date(2026, 12, 31), -1),
            (datetime.date(2026, 7, 1), datetime.date(2026, 9, 30)),
        )
        self.assertEqual(
            services.periode_voisine('annee', datetime.date(2026, 1, 1), datetime.date(2026, 12, 31), 1),
            (datetime.date(2027, 1, 1), datetime.date(2027, 12, 31)),
        )

    def test_personnalisee_se_decale_de_sa_propre_duree(self):
        debut, fin = datetime.date(2026, 9, 1), datetime.date(2026, 9, 10)  # 10 jours

        self.assertEqual(
            services.periode_voisine('perso', debut, fin, -1),
            (datetime.date(2026, 8, 22), datetime.date(2026, 8, 31)),
        )
        self.assertEqual(
            services.periode_voisine('perso', debut, fin, 1),
            (datetime.date(2026, 9, 11), datetime.date(2026, 9, 20)),
        )


class SyntheseTests(TestCase):
    def test_compte_les_seances_passees_et_les_inscrits(self):
        inscrire(creer_seance(jours=-3, capacite=10), 5)
        inscrire(creer_seance(jours=-2, capacite=10), 3)

        synthese = services.calculer(filtres_larges())['synthese']

        self.assertEqual(synthese['seances'], 2)
        self.assertEqual(synthese['inscrits'], 8)

    def test_remplissage_est_pondere_par_la_capacite(self):
        inscrire(creer_seance(jours=-3, capacite=10), 10)
        inscrire(creer_seance(jours=-2, capacite=30), 0)

        synthese = services.calculer(filtres_larges())['synthese']

        self.assertEqual(synthese['remplissage'], 25.0)  # 10 / 40

    def test_ignore_les_seances_futures(self):
        creer_seance(jours=2)

        synthese = services.calculer(filtres_larges(fin=timezone.localdate() + datetime.timedelta(days=5)))['synthese']

        self.assertEqual(synthese['seances'], 0)

    def test_ignore_les_seances_hors_periode(self):
        creer_seance(jours=-100)

        self.assertEqual(services.calculer(filtres_larges())['synthese']['seances'], 0)

    def test_la_date_de_fin_est_incluse(self):
        creer_seance(jours=0, heure=0)  # aujourd'hui à minuit, déjà passée

        self.assertEqual(services.calculer(filtres_larges())['synthese']['seances'], 1)

    def test_les_non_presents_occupent_une_place_mais_pas_les_desinscrits(self):
        seance = creer_seance(capacite=10)
        inscrire(seance, 2, Inscription.Statut.INSCRIT)
        inscrire(seance, 1, Inscription.Statut.NON_PRESENTE)
        inscrire(seance, 4, Inscription.Statut.DESINSCRIT)
        inscrire(seance, 1, Inscription.Statut.DESINSCRIT_TARDIF_JOKER)
        inscrire(seance, 1, Inscription.Statut.EN_ATTENTE)

        self.assertEqual(services.calculer(filtres_larges())['synthese']['inscrits'], 3)

    def test_sans_seance_le_remplissage_vaut_zero(self):
        synthese = services.calculer(filtres_larges())['synthese']

        self.assertEqual(synthese['remplissage'], 0)
        self.assertEqual(synthese['moyenne_inscrits'], 0)

    def test_moyenne_d_inscrits_par_seance(self):
        inscrire(creer_seance(jours=-3), 6)
        inscrire(creer_seance(jours=-2), 2)

        self.assertEqual(services.calculer(filtres_larges())['synthese']['moyenne_inscrits'], 4.0)


class FiltresTests(TestCase):
    def test_filtre_par_nom_de_seance(self):
        creer_seance(nom='WOD')
        creer_seance(nom='Cross', jours=-2)

        resultat = services.calculer(filtres_larges(nom='Cross'))

        self.assertEqual(resultat['synthese']['seances'], 1)

    def test_filtre_par_coach(self):
        loic = User.objects.create_user(username='loic', role=User.Role.GESTIONNAIRE)
        sam = User.objects.create_user(username='sam', role=User.Role.COACH)
        creer_seance(coach=loic)
        creer_seance(coach=sam, jours=-2)

        resultat = services.calculer(filtres_larges(coach_id=sam.pk))

        self.assertEqual(resultat['synthese']['seances'], 1)

    def test_liste_les_noms_de_seance_disponibles(self):
        creer_seance(nom='WOD')
        creer_seance(nom='Cross', jours=-2)
        creer_seance(nom='WOD', jours=-4)

        self.assertEqual(services.noms_de_seances(), ['Cross', 'WOD'])


class VentilationTests(TestCase):
    def test_par_type_de_seance(self):
        inscrire(creer_seance(nom='WOD', capacite=10), 8)
        inscrire(creer_seance(nom='WOD', jours=-2, capacite=10), 4)
        inscrire(creer_seance(nom='Cross', jours=-4, capacite=10), 5)

        lignes = {l['libelle']: l for l in services.calculer(filtres_larges())['par_type']}

        self.assertEqual(lignes['WOD']['seances'], 2)
        self.assertEqual(lignes['WOD']['inscrits'], 12)
        self.assertEqual(lignes['WOD']['remplissage'], 60.0)
        self.assertEqual(lignes['Cross']['remplissage'], 50.0)

    def test_par_type_est_classe_par_nombre_d_inscrits_decroissant(self):
        inscrire(creer_seance(nom='Petit'), 1)
        inscrire(creer_seance(nom='Grand', jours=-2), 9)

        libelles = [l['libelle'] for l in services.calculer(filtres_larges())['par_type']]

        self.assertEqual(libelles, ['Grand', 'Petit'])

    def test_par_coach_inclut_les_seances_sans_coach(self):
        loic = User.objects.create_user(username='loic2', first_name='Loïc', role=User.Role.GESTIONNAIRE)
        creer_seance(coach=loic)
        creer_seance(coach=None, jours=-2)

        libelles = {l['libelle'] for l in services.calculer(filtres_larges())['par_coach']}

        self.assertEqual(libelles, {'Loïc', 'Sans coach'})

    def test_compte_les_seances_sous_le_seuil_par_type(self):
        inscrire(creer_seance(nom='WOD'), 3)
        inscrire(creer_seance(nom='WOD', jours=-2), 4)

        ligne = services.calculer(filtres_larges())['par_type'][0]

        self.assertEqual(ligne['sous_seuil'], 1)


class SeancesSousSeuilTests(TestCase):
    def test_liste_les_seances_en_dessous_de_4_inscrits(self):
        faible = creer_seance(nom='Faible')
        inscrire(faible, 3)
        inscrire(creer_seance(nom='Bonne', jours=-2), 4)

        liste = services.calculer(filtres_larges())['sous_seuil']

        self.assertEqual([s['seance'].pk for s in liste], [faible.pk])
        self.assertEqual(liste[0]['inscrits'], 3)


class EvolutionTests(TestCase):
    def test_regroupe_par_semaine_sur_une_periode_courte(self):
        inscrire(creer_seance(jours=-3), 4)
        inscrire(creer_seance(jours=-20), 6)

        resultat = services.calculer(filtres_larges(debut=timezone.localdate() - datetime.timedelta(days=30)))

        self.assertEqual(resultat['evolution']['granularite'], 'semaine')
        self.assertEqual(sum(resultat['evolution']['inscrits']), 10)
        self.assertEqual(len(resultat['evolution']['libelles']), len(resultat['evolution']['inscrits']))

    def test_regroupe_par_mois_sur_une_longue_periode(self):
        inscrire(creer_seance(jours=-3), 4)

        resultat = services.calculer(filtres_larges(debut=timezone.localdate() - datetime.timedelta(days=300)))

        self.assertEqual(resultat['evolution']['granularite'], 'mois')
        self.assertEqual(sum(resultat['evolution']['inscrits']), 4)

    def test_les_periodes_sans_seance_apparaissent_a_zero(self):
        inscrire(creer_seance(jours=-3), 4)

        resultat = services.calculer(filtres_larges(debut=timezone.localdate() - datetime.timedelta(days=30)))

        self.assertIn(0, resultat['evolution']['seances'])


class HeatmapTests(TestCase):
    def test_remplissage_moyen_par_creneau_jour_et_heure(self):
        seance = creer_seance(jours=-3, heure=18, capacite=10)
        inscrire(seance, 5)
        jour_semaine = timezone.localtime(seance.debut).weekday()

        heatmap = services.calculer(filtres_larges())['heatmap']

        self.assertEqual(heatmap['heures'], [18])
        self.assertEqual(heatmap['cases'][18][jour_semaine]['remplissage'], 50.0)
        self.assertEqual(heatmap['cases'][18][jour_semaine]['seances'], 1)

    def test_creneau_sans_seance_est_vide(self):
        seance = creer_seance(jours=-3, heure=18)
        jour_semaine = timezone.localtime(seance.debut).weekday()

        heatmap = services.calculer(filtres_larges())['heatmap']

        autre_jour = (jour_semaine + 1) % 7
        self.assertIsNone(heatmap['cases'][18][autre_jour])


class VueStatistiquesTests(TestCase):
    def setUp(self):
        self.gestionnaire = User.objects.create_user(username='gest_stats', role=User.Role.GESTIONNAIRE)
        self.url = reverse('statistiques:tableau_de_bord')

    def test_accessible_au_gestionnaire(self):
        self.client.force_login(self.gestionnaire)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_accessible_a_l_admin(self):
        admin = User.objects.create_user(username='admin_stats', role=User.Role.ADMIN)
        self.client.force_login(admin)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_refusee_au_coach(self):
        coach = User.objects.create_user(username='coach_stats', role=User.Role.COACH)
        self.client.force_login(coach)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_refusee_au_membre(self):
        membre = User.objects.create_user(username='membre_stats', role=User.Role.MEMBRE)
        self.client.force_login(membre)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_redirige_un_visiteur_vers_la_connexion(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_affiche_les_chiffres_de_la_periode(self):
        inscrire(creer_seance(nom='WOD Spécial', jours=0, heure=0), 4)
        self.client.force_login(self.gestionnaire)

        response = self.client.get(self.url, {'periode': 'annee'})

        self.assertContains(response, 'WOD Spécial')

    def test_applique_le_filtre_par_type(self):
        creer_seance(nom='WOD Spécial', jours=0, heure=0)
        creer_seance(nom='Cross Autre', jours=0, heure=1)
        self.client.force_login(self.gestionnaire)

        response = self.client.get(self.url, {'periode': 'annee', 'type': 'Cross Autre'})

        self.assertEqual(response.context['resultat']['synthese']['seances'], 1)

    def test_un_coach_inconnu_ou_invalide_est_ignore(self):
        self.client.force_login(self.gestionnaire)
        self.assertEqual(self.client.get(self.url, {'coach': 'abc'}).status_code, 200)

    def test_le_parametre_ref_affiche_la_periode_contenant_cette_date(self):
        self.client.force_login(self.gestionnaire)

        response = self.client.get(self.url, {'periode': 'mois', 'ref': '2026-03-15'})

        self.assertEqual(response.context['debut'], datetime.date(2026, 3, 1))
        self.assertEqual(response.context['fin'], datetime.date(2026, 3, 31))

    def test_un_ref_invalide_est_ignore(self):
        self.client.force_login(self.gestionnaire)

        response = self.client.get(self.url, {'periode': 'mois', 'ref': 'pas-une-date'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['debut'], timezone.localdate().replace(day=1))

    def test_lien_vers_la_periode_precedente_conserve_les_filtres(self):
        self.client.force_login(self.gestionnaire)

        response = self.client.get(self.url, {'periode': 'mois', 'ref': '2026-03-15', 'type': 'WOD'})

        precedent = response.context['url_precedent']
        self.assertIn('periode=mois', precedent)
        self.assertIn('ref=2026-02-28', precedent)
        self.assertIn('type=WOD', precedent)

    def test_lien_suivant_present_pour_une_periode_passee(self):
        self.client.force_login(self.gestionnaire)

        response = self.client.get(self.url, {'periode': 'mois', 'ref': '2026-03-15'})

        self.assertIn('ref=2026-04-01', response.context['url_suivant'])

    def test_pas_de_lien_suivant_quand_la_periode_contient_aujourd_hui(self):
        self.client.force_login(self.gestionnaire)

        response = self.client.get(self.url, {'periode': 'mois'})

        self.assertIsNone(response.context['url_suivant'])

    def test_navigation_personnalisee_utilise_debut_et_fin(self):
        self.client.force_login(self.gestionnaire)

        response = self.client.get(self.url, {'periode': 'perso', 'debut': '2026-03-01', 'fin': '2026-03-10'})

        self.assertIn('debut=2026-02-19', response.context['url_precedent'])
        self.assertIn('fin=2026-02-28', response.context['url_precedent'])
        self.assertIn('debut=2026-03-11', response.context['url_suivant'])

    def test_les_donnees_changent_avec_la_periode_naviguee(self):
        inscrire(creer_seance(nom='Séance ancienne', jours=-100, heure=10), 2)
        self.client.force_login(self.gestionnaire)
        ancienne = timezone.localdate() - datetime.timedelta(days=100)

        response = self.client.get(self.url, {'periode': 'mois', 'ref': ancienne.isoformat()})

        self.assertEqual(response.context['resultat']['synthese']['seances'], 1)

    def test_lien_dans_le_menu_pour_le_gestionnaire(self):
        self.client.force_login(self.gestionnaire)
        response = self.client.get(reverse('home'), follow=True)
        self.assertContains(response, self.url)

    def test_pas_de_lien_dans_le_menu_pour_un_membre(self):
        membre = User.objects.create_user(username='membre_menu_stats', role=User.Role.MEMBRE)
        self.client.force_login(membre)
        response = self.client.get(reverse('home'), follow=True)
        self.assertNotContains(response, self.url)
