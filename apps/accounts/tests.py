import re
from urllib.parse import urlparse

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.bookings.services import solde_jokers

from .backends import CaseInsensitiveModelBackend
from .forms import FamilleForm, MembreCreateForm, MembreUpdateForm, ProfilForm
from .models import Famille, User


class RoleCoachSimpleTests(TestCase):
    def test_coach_gestionnaire_garde_les_droits_actuels(self):
        gestionnaire = User(role=User.Role.GESTIONNAIRE)

        self.assertTrue(gestionnaire.is_staff_or_manager)
        self.assertTrue(gestionnaire.peut_marquer_absence)

    def test_coach_simple_n_a_pas_les_droits_de_gestion(self):
        coach = User(role=User.Role.COACH)

        self.assertFalse(coach.is_staff_or_manager)
        self.assertTrue(coach.is_coach)

    def test_coach_simple_peut_marquer_une_absence(self):
        coach = User(role=User.Role.COACH)

        self.assertTrue(coach.peut_marquer_absence)

    def test_membre_ne_peut_pas_marquer_une_absence(self):
        membre = User(role=User.Role.MEMBRE)

        self.assertFalse(membre.peut_marquer_absence)

    def test_le_label_du_role_gestionnaire_est_coach_gestionnaire(self):
        self.assertEqual(User.Role.GESTIONNAIRE.label, 'Coach gestionnaire')

    def test_le_label_du_role_coach_est_coach(self):
        self.assertEqual(User.Role.COACH.label, 'Coach')


def creer_gestionnaire(**kwargs):
    kwargs.setdefault('username', 'coach1')
    kwargs.setdefault('role', User.Role.GESTIONNAIRE)
    return User.objects.create_user(password='motdepasse123', **kwargs)


class MembreCreateFormTests(TestCase):
    def test_cree_un_membre_par_defaut(self):
        form = MembreCreateForm(data={
            'username': 'jdupont',
            'role': User.Role.MEMBRE,
            'email': 'jdupont@example.com',
            'tolerance_seances_negatives': 0,
        })

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.role, User.Role.MEMBRE)

    def test_le_compte_cree_n_a_pas_de_mot_de_passe_utilisable(self):
        form = MembreCreateForm(data={
            'username': 'jdupont_mdp',
            'role': User.Role.MEMBRE,
            'email': 'jdupont_mdp@example.com',
            'tolerance_seances_negatives': 0,
        })

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertFalse(user.has_usable_password())

    def test_refuse_sans_email(self):
        form = MembreCreateForm(data={
            'username': 'sans_email',
            'role': User.Role.MEMBRE,
            'tolerance_seances_negatives': 0,
        })

        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_un_nouveau_membre_recoit_un_joker(self):
        form = MembreCreateForm(data={
            'username': 'jdupont2',
            'role': User.Role.MEMBRE,
            'email': 'jdupont2@example.com',
            'tolerance_seances_negatives': 0,
        })

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(solde_jokers(user), 1)

    def test_un_nouveau_coach_ne_recoit_pas_de_joker(self):
        form = MembreCreateForm(data={
            'username': 'jcoach2',
            'role': User.Role.GESTIONNAIRE,
            'email': 'jcoach2@example.com',
            'tolerance_seances_negatives': 0,
        })

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(solde_jokers(user), 0)

    def test_peut_creer_un_coach(self):
        form = MembreCreateForm(data={
            'username': 'jcoach',
            'role': User.Role.GESTIONNAIRE,
            'email': 'jcoach@example.com',
            'tolerance_seances_negatives': 0,
        })

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.role, User.Role.GESTIONNAIRE)
        self.assertTrue(user.is_gestionnaire)

    def test_refuse_le_role_admin(self):
        form = MembreCreateForm(data={
            'username': 'jadmin',
            'role': User.Role.ADMIN,
            'email': 'jadmin@example.com',
            'tolerance_seances_negatives': 0,
        })

        self.assertFalse(form.is_valid())
        self.assertIn('role', form.errors)


class MembreUpdateFormTests(TestCase):
    def test_peut_changer_un_membre_en_coach(self):
        membre = User.objects.create(username='futur_coach', role=User.Role.MEMBRE)

        form = MembreUpdateForm(data={
            'username': membre.username,
            'role': User.Role.GESTIONNAIRE,
            'tolerance_seances_negatives': 0,
        }, instance=membre)

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertTrue(user.is_gestionnaire)


class MembreUpdateViewTests(TestCase):
    def test_consulter_une_fiche_ne_change_pas_l_utilisateur_connecte_dans_le_contexte(self):
        gestionnaire = creer_gestionnaire()
        membre = User.objects.create(username='membre_consulte', role=User.Role.MEMBRE)
        self.client.force_login(gestionnaire)

        response = self.client.get(reverse('accounts:membre_modifier', args=[membre.pk]))

        self.assertEqual(response.context['user'], gestionnaire)
        self.assertEqual(response.context['membre'], membre)

    def test_expose_le_solde_de_jokers_du_membre(self):
        gestionnaire = creer_gestionnaire()
        membre = User.objects.create(username='membre_joker', role=User.Role.MEMBRE)
        self.client.force_login(gestionnaire)

        response = self.client.get(reverse('accounts:membre_modifier', args=[membre.pk]))

        self.assertEqual(response.context['solde_jokers'], 0)

    def test_propose_d_attribuer_un_joker_si_le_membre_n_en_a_pas(self):
        gestionnaire = creer_gestionnaire()
        membre = User.objects.create(username='sans_joker_fiche', role=User.Role.MEMBRE)
        self.client.force_login(gestionnaire)

        response = self.client.get(reverse('accounts:membre_modifier', args=[membre.pk]))

        self.assertContains(response, 'Attribuer un joker')

    def test_propose_de_retirer_le_joker_si_le_membre_en_a_un(self):
        from apps.bookings.models import MouvementJoker

        gestionnaire = creer_gestionnaire()
        membre = User.objects.create(username='avec_joker_fiche', role=User.Role.MEMBRE)
        MouvementJoker.objects.create(membre=membre, delta=1, motif=MouvementJoker.Motif.ATTRIBUTION)
        self.client.force_login(gestionnaire)

        response = self.client.get(reverse('accounts:membre_modifier', args=[membre.pk]))

        self.assertContains(response, 'Retirer le joker')


class MembreUpdateViewSoldeAffichageTests(TestCase):
    def test_le_solde_est_affiche_sur_la_fiche_d_un_membre(self):
        gestionnaire = creer_gestionnaire()
        membre = User.objects.create(username='membre_fiche_solde', role=User.Role.MEMBRE)
        self.client.force_login(gestionnaire)

        response = self.client.get(reverse('accounts:membre_modifier', args=[membre.pk]))

        self.assertContains(response, 'badge-solde')

    def test_le_solde_n_est_pas_affiche_sur_la_fiche_d_un_coach(self):
        gestionnaire = creer_gestionnaire()
        coach = User.objects.create(username='coach_fiche_sans_solde', role=User.Role.COACH)
        self.client.force_login(gestionnaire)

        response = self.client.get(reverse('accounts:membre_modifier', args=[coach.pk]))

        self.assertNotContains(response, 'badge-solde')
        self.assertNotContains(response, 'Historique')


class MembreListViewTests(TestCase):
    def test_les_comptes_coach_apparaissent_dans_la_liste(self):
        gestionnaire = creer_gestionnaire()
        coach = creer_gestionnaire(username='autre_coach')
        self.client.force_login(gestionnaire)

        response = self.client.get(reverse('accounts:membre_liste'))

        self.assertContains(response, 'autre_coach')
        self.assertContains(response, coach.get_role_display())

    def test_les_comptes_coach_simple_apparaissent_dans_la_liste(self):
        gestionnaire = creer_gestionnaire()
        coach_simple = User.objects.create_user(
            username='coach_simple_liste', password='motdepasse123', role=User.Role.COACH
        )
        self.client.force_login(gestionnaire)

        response = self.client.get(reverse('accounts:membre_liste'))

        self.assertContains(response, 'coach_simple_liste')

    def test_un_coach_simple_a_le_badge_visuel_coach(self):
        admin = User.objects.create_user(username='admin_badge', password='motdepasse123', role=User.Role.ADMIN)
        User.objects.create_user(
            username='coach_simple_badge', password='motdepasse123', role=User.Role.COACH
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('accounts:membre_liste'))

        self.assertContains(response, 'card p-3 card-clickable card-coach')

    def test_un_coach_simple_ne_peut_pas_acceder_a_la_liste_des_comptes(self):
        coach_simple = User.objects.create_user(
            username='coach_simple_interdit', password='motdepasse123', role=User.Role.COACH
        )
        self.client.force_login(coach_simple)

        response = self.client.get(reverse('accounts:membre_liste'))

        self.assertEqual(response.status_code, 403)


class MembreListViewSoldeAffichageTests(TestCase):
    def test_le_solde_est_affiche_pour_un_membre(self):
        gestionnaire = creer_gestionnaire()
        User.objects.create(username='membre_solde_liste', role=User.Role.MEMBRE)
        self.client.force_login(gestionnaire)

        response = self.client.get(reverse('accounts:membre_liste'))

        self.assertContains(response, 'badge-solde')

    def test_le_solde_n_est_pas_affiche_pour_un_coach(self):
        gestionnaire = creer_gestionnaire()
        User.objects.create(username='coach_sans_solde', role=User.Role.COACH)
        self.client.force_login(gestionnaire)

        response = self.client.get(reverse('accounts:membre_liste'))

        self.assertNotContains(response, 'badge-solde')

    def test_le_solde_n_est_pas_affiche_pour_un_coach_gestionnaire(self):
        gestionnaire = creer_gestionnaire()
        User.objects.create(username='autre_gestionnaire_sans_solde', role=User.Role.GESTIONNAIRE)
        self.client.force_login(gestionnaire)

        response = self.client.get(reverse('accounts:membre_liste'))

        self.assertNotContains(response, 'badge-solde')

    def test_les_boutons_d_ajustement_n_apparaissent_pas_pour_un_coach(self):
        gestionnaire = creer_gestionnaire()
        User.objects.create(username='coach_sans_ajustement', role=User.Role.COACH)
        self.client.force_login(gestionnaire)

        response = self.client.get(reverse('accounts:membre_liste'))

        self.assertNotContains(response, 'ajuster_solde')


class MembreToggleActifViewTests(TestCase):
    def test_un_gestionnaire_peut_desactiver_un_compte_coach(self):
        gestionnaire = creer_gestionnaire()
        coach = creer_gestionnaire(username='coach_a_desactiver')
        self.client.force_login(gestionnaire)

        self.client.post(reverse('accounts:membre_toggle_actif', args=[coach.pk]))

        coach.refresh_from_db()
        self.assertFalse(coach.is_active)


class MembreCreateViewEmailTests(TestCase):
    def setUp(self):
        self.gestionnaire = creer_gestionnaire()
        self.client.force_login(self.gestionnaire)

    def test_envoie_un_email_avec_le_login_et_un_lien_pour_definir_le_mot_de_passe(self):
        response = self.client.post(reverse('accounts:membre_creer'), {
            'username': 'nouveau_membre_email',
            'role': User.Role.MEMBRE,
            'email': 'nouveau_membre_email@example.com',
            'tolerance_seances_negatives': 0,
        })

        self.assertRedirects(response, reverse('accounts:membre_liste'))
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['nouveau_membre_email@example.com'])
        self.assertIn('nouveau_membre_email', email.body)
        self.assertIn('/comptes/mot-de-passe/reinitialiser/', email.body)

    def test_le_lien_recu_permet_de_definir_le_mot_de_passe(self):
        self.client.post(reverse('accounts:membre_creer'), {
            'username': 'membre_lien_mdp',
            'role': User.Role.MEMBRE,
            'email': 'membre_lien_mdp@example.com',
            'tolerance_seances_negatives': 0,
        })
        membre = User.objects.get(username='membre_lien_mdp')
        self.assertFalse(membre.has_usable_password())

        lien = re.search(r'https?://\S+/comptes/mot-de-passe/reinitialiser/\S+', mail.outbox[0].body).group(0)
        chemin = urlparse(lien).path

        reponse_lien = self.client.get(chemin, follow=True)
        self.assertTrue(reponse_lien.context['validlink'])

        reponse_post = self.client.post(reponse_lien.request['PATH_INFO'], {
            'new_password1': 'motdepassechoisi123!',
            'new_password2': 'motdepassechoisi123!',
        })

        self.assertRedirects(reponse_post, reverse('accounts:password_reset_complete'))
        membre.refresh_from_db()
        self.assertTrue(membre.check_password('motdepassechoisi123!'))


class AdminSiteAccessTests(TestCase):
    def test_un_coach_meme_avec_is_staff_ne_peut_pas_acceder_a_l_admin(self):
        coach = User.objects.create_user(
            username='coach_admin_test',
            password='motdepasse123',
            role=User.Role.GESTIONNAIRE,
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(coach)

        response = self.client.get('/admin/')

        self.assertNotEqual(response.status_code, 200)

    def test_un_admin_peut_acceder_a_l_admin(self):
        admin = User.objects.create_user(
            username='admin_test',
            password='motdepasse123',
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(admin)

        response = self.client.get('/admin/')

        self.assertEqual(response.status_code, 200)


class PasswordResetTests(TestCase):
    def test_le_formulaire_de_demande_s_affiche(self):
        response = self.client.get(reverse('accounts:password_reset'))

        self.assertEqual(response.status_code, 200)

    def test_envoie_un_email_avec_un_lien_de_reinitialisation(self):
        User.objects.create_user(username='oubli', password='ancien123', email='oubli@example.com')

        response = self.client.post(reverse('accounts:password_reset'), {'email': 'oubli@example.com'})

        self.assertRedirects(response, reverse('accounts:password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Le Garage', mail.outbox[0].subject)
        self.assertIn('/comptes/mot-de-passe/reinitialiser/', mail.outbox[0].body)

    def test_aucun_email_envoye_si_l_adresse_est_inconnue(self):
        response = self.client.post(reverse('accounts:password_reset'), {'email': 'inconnu@example.com'})

        self.assertRedirects(response, reverse('accounts:password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_le_lien_recu_permet_de_definir_un_nouveau_mot_de_passe(self):
        membre = User.objects.create_user(username='oubli2', password='ancien123', email='oubli2@example.com')

        self.client.post(reverse('accounts:password_reset'), {'email': 'oubli2@example.com'})
        lien = re.search(r'https?://\S+/comptes/mot-de-passe/reinitialiser/\S+', mail.outbox[0].body).group(0)
        chemin = urlparse(lien).path

        reponse_lien = self.client.get(chemin, follow=True)
        self.assertTrue(reponse_lien.context['validlink'])

        reponse_post = self.client.post(reponse_lien.request['PATH_INFO'], {
            'new_password1': 'nouveaumdp123!',
            'new_password2': 'nouveaumdp123!',
        })

        self.assertRedirects(reponse_post, reverse('accounts:password_reset_complete'))
        membre.refresh_from_db()
        self.assertTrue(membre.check_password('nouveaumdp123!'))


class ProfilFormTests(TestCase):
    def test_n_expose_pas_le_role_ni_la_tolerance(self):
        form = ProfilForm()

        self.assertEqual(set(form.fields), {'first_name', 'last_name', 'email', 'telephone'})


class ProfilUpdateViewTests(TestCase):
    def test_necessite_d_etre_connecte(self):
        response = self.client.get(reverse('accounts:profil_modifier'))

        self.assertNotEqual(response.status_code, 200)

    def test_un_membre_peut_modifier_son_profil(self):
        membre = User.objects.create_user(username='auto_edit', password='motdepasse123')
        self.client.force_login(membre)

        response = self.client.post(reverse('accounts:profil_modifier'), {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'email': 'jean.dupont@example.com',
            'telephone': '0612345678',
        })

        self.assertRedirects(response, reverse('accounts:preferences'))
        membre.refresh_from_db()
        self.assertEqual(membre.first_name, 'Jean')
        self.assertEqual(membre.last_name, 'Dupont')
        self.assertEqual(membre.email, 'jean.dupont@example.com')
        self.assertEqual(membre.telephone, '0612345678')

    def test_ne_peut_pas_changer_son_propre_role(self):
        membre = User.objects.create_user(username='auto_edit_role', password='motdepasse123', role=User.Role.MEMBRE)
        self.client.force_login(membre)

        self.client.post(reverse('accounts:profil_modifier'), {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'email': 'jean@example.com',
            'telephone': '',
            'role': User.Role.GESTIONNAIRE,
        })

        membre.refresh_from_db()
        self.assertEqual(membre.role, User.Role.MEMBRE)

    def test_ne_modifie_que_l_utilisateur_connecte(self):
        membre = User.objects.create_user(username='auto_edit_self', password='motdepasse123')
        autre = User.objects.create(username='intouche', first_name='Original')
        self.client.force_login(membre)

        self.client.post(reverse('accounts:profil_modifier'), {
            'first_name': 'Jean', 'last_name': 'Dupont', 'email': 'jean@example.com', 'telephone': '',
        })

        autre.refresh_from_db()
        self.assertEqual(autre.first_name, 'Original')


class CaseInsensitiveModelBackendTests(TestCase):
    def test_authenticate_reussit_avec_une_casse_differente(self):
        User.objects.create_user(username='JeanDupont', password='motdepasse123')
        backend = CaseInsensitiveModelBackend()

        user = backend.authenticate(request=None, username='jeandupont', password='motdepasse123')

        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'JeanDupont')

    def test_authenticate_echoue_si_mot_de_passe_incorrect(self):
        User.objects.create_user(username='JeanDupont', password='motdepasse123')
        backend = CaseInsensitiveModelBackend()

        user = backend.authenticate(request=None, username='jeandupont', password='mauvais')

        self.assertIsNone(user)

    def test_authenticate_echoue_si_username_inconnu(self):
        backend = CaseInsensitiveModelBackend()

        user = backend.authenticate(request=None, username='inconnu', password='motdepasse123')

        self.assertIsNone(user)


class FamilleFormTests(TestCase):
    def test_cree_une_famille_avec_nom_et_tolerance(self):
        form = FamilleForm(data={'nom': 'Famille Dupont', 'tolerance_seances_negatives': 2})

        self.assertTrue(form.is_valid(), form.errors)
        famille = form.save()
        self.assertEqual(famille.nom, 'Famille Dupont')
        self.assertEqual(famille.tolerance_seances_negatives, 2)

    def test_refuse_une_famille_sans_nom(self):
        form = FamilleForm(data={'nom': '', 'tolerance_seances_negatives': 0})

        self.assertFalse(form.is_valid())
        self.assertIn('nom', form.errors)


class FamilleCreerAjaxViewTests(TestCase):
    def test_un_gestionnaire_peut_creer_une_famille_en_ajax(self):
        gestionnaire = creer_gestionnaire()
        self.client.force_login(gestionnaire)

        response = self.client.post(reverse('accounts:famille_creer_ajax'), {
            'nom': 'Famille Martin',
            'tolerance_seances_negatives': 1,
        })

        self.assertEqual(response.status_code, 201)
        data = response.json()
        famille = Famille.objects.get(pk=data['id'])
        self.assertEqual(famille.nom, 'Famille Martin')
        self.assertEqual(data['nom'], 'Famille Martin')

    def test_un_membre_ne_peut_pas_creer_de_famille(self):
        membre = User.objects.create_user(
            username='membre_famille', password='motdepasse123', role=User.Role.MEMBRE
        )
        self.client.force_login(membre)

        response = self.client.post(reverse('accounts:famille_creer_ajax'), {
            'nom': 'Famille Interdite',
            'tolerance_seances_negatives': 0,
        })

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Famille.objects.filter(nom='Famille Interdite').exists())

    def test_un_coach_simple_ne_peut_pas_creer_de_famille(self):
        coach = User.objects.create_user(
            username='coach_simple_famille', password='motdepasse123', role=User.Role.COACH
        )
        self.client.force_login(coach)

        response = self.client.post(reverse('accounts:famille_creer_ajax'), {
            'nom': 'Famille Interdite 2',
            'tolerance_seances_negatives': 0,
        })

        self.assertEqual(response.status_code, 403)

    def test_donnees_invalides_renvoie_400_avec_erreurs(self):
        gestionnaire = creer_gestionnaire()
        self.client.force_login(gestionnaire)

        response = self.client.post(reverse('accounts:famille_creer_ajax'), {
            'nom': '',
            'tolerance_seances_negatives': 0,
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn('nom', response.json()['errors'])


class MembreFormFamilleTests(TestCase):
    def test_le_formulaire_de_creation_propose_un_lien_pour_creer_une_famille(self):
        gestionnaire = creer_gestionnaire()
        self.client.force_login(gestionnaire)

        response = self.client.get(reverse('accounts:membre_creer'))

        self.assertContains(response, 'Nouvelle famille')
        self.assertContains(response, reverse('accounts:famille_creer_ajax'))


class AnimeDesSeancesTests(TestCase):
    def test_un_coach_anime_des_seances(self):
        coach = User(role=User.Role.COACH)

        self.assertTrue(coach.anime_des_seances)

    def test_un_gestionnaire_anime_des_seances(self):
        gestionnaire = User(role=User.Role.GESTIONNAIRE)

        self.assertTrue(gestionnaire.anime_des_seances)

    def test_un_admin_anime_des_seances(self):
        admin = User(role=User.Role.ADMIN)

        self.assertTrue(admin.anime_des_seances)

    def test_un_membre_n_anime_pas_de_seances(self):
        membre = User(role=User.Role.MEMBRE)

        self.assertFalse(membre.anime_des_seances)


class TopicNtfyCoachTests(TestCase):
    def test_un_coach_recoit_un_topic_ntfy_a_la_creation(self):
        coach = User.objects.create(username='coach_topic', role=User.Role.COACH)

        self.assertTrue(coach.topic_ntfy_coach)
        self.assertTrue(coach.topic_ntfy_coach.startswith('garage-coach-'))

    def test_un_membre_ne_recoit_pas_de_topic_ntfy(self):
        membre = User.objects.create(username='membre_topic', role=User.Role.MEMBRE)

        self.assertFalse(membre.topic_ntfy_coach)

    def test_le_topic_n_est_pas_regenere_a_chaque_sauvegarde(self):
        coach = User.objects.create(username='coach_stable', role=User.Role.COACH)
        premier_topic = coach.topic_ntfy_coach

        coach.first_name = 'Jean'
        coach.save()

        self.assertEqual(coach.topic_ntfy_coach, premier_topic)

    def test_deux_coachs_ont_des_topics_differents(self):
        coach1 = User.objects.create(username='coach_a', role=User.Role.COACH)
        coach2 = User.objects.create(username='coach_b', role=User.Role.COACH)

        self.assertNotEqual(coach1.topic_ntfy_coach, coach2.topic_ntfy_coach)


class PreferencesNotificationCoachTests(TestCase):
    def test_les_4_preferences_sont_activees_par_defaut(self):
        coach = User.objects.create(username='coach_prefs_defaut', role=User.Role.COACH)

        self.assertTrue(coach.notifie_inscription)
        self.assertTrue(coach.notifie_desinscription)
        self.assertTrue(coach.notifie_promotion_automatique)
        self.assertTrue(coach.notifie_seance_complete)

    def test_coachs_suivis_est_vide_par_defaut(self):
        gestionnaire = creer_gestionnaire(username='gestionnaire_suivi_defaut')

        self.assertEqual(list(gestionnaire.coachs_suivis.all()), [])

    def test_peut_suivre_des_coachs_precis(self):
        gestionnaire = creer_gestionnaire(username='gestionnaire_suivi')
        coach_a = User.objects.create(username='coach_suivi_a', role=User.Role.COACH)

        gestionnaire.coachs_suivis.add(coach_a)

        self.assertIn(coach_a, gestionnaire.coachs_suivis.all())

    def test_suivre_un_coach_ne_le_fait_pas_apparaitre_dans_ses_propres_suivis(self):
        gestionnaire = creer_gestionnaire(username='gestionnaire_suivi2')
        coach_a = User.objects.create(username='coach_suivi_b', role=User.Role.COACH)

        gestionnaire.coachs_suivis.add(coach_a)

        self.assertEqual(list(coach_a.coachs_suivis.all()), [])


class ConnexionInsensibleCasseTests(TestCase):
    def test_connexion_avec_une_casse_differente_fonctionne(self):
        User.objects.create_user(username='JeanDupont', password='motdepasse123')

        connecte = self.client.login(username='jeandupont', password='motdepasse123')

        self.assertTrue(connecte)

    def test_connexion_avec_un_mauvais_mot_de_passe_echoue_toujours(self):
        User.objects.create_user(username='JeanDupont', password='motdepasse123')

        connecte = self.client.login(username='jeandupont', password='mauvais')

        self.assertFalse(connecte)
