import re
from urllib.parse import urlparse

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.bookings.services import solde_jokers

from .forms import MembreCreateForm, MembreUpdateForm, ProfilForm
from .models import User


def creer_gestionnaire(**kwargs):
    kwargs.setdefault('username', 'coach1')
    kwargs.setdefault('role', User.Role.GESTIONNAIRE)
    return User.objects.create_user(password='motdepasse123', **kwargs)


class MembreCreateFormTests(TestCase):
    def test_cree_un_membre_par_defaut(self):
        form = MembreCreateForm(data={
            'username': 'jdupont',
            'role': User.Role.MEMBRE,
            'password1': 'motdepasse123',
            'password2': 'motdepasse123',
            'tolerance_seances_negatives': 0,
        })

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.role, User.Role.MEMBRE)

    def test_un_nouveau_membre_recoit_un_joker(self):
        form = MembreCreateForm(data={
            'username': 'jdupont2',
            'role': User.Role.MEMBRE,
            'password1': 'motdepasse123',
            'password2': 'motdepasse123',
            'tolerance_seances_negatives': 0,
        })

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(solde_jokers(user), 1)

    def test_un_nouveau_coach_ne_recoit_pas_de_joker(self):
        form = MembreCreateForm(data={
            'username': 'jcoach2',
            'role': User.Role.GESTIONNAIRE,
            'password1': 'motdepasse123',
            'password2': 'motdepasse123',
            'tolerance_seances_negatives': 0,
        })

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(solde_jokers(user), 0)

    def test_peut_creer_un_coach(self):
        form = MembreCreateForm(data={
            'username': 'jcoach',
            'role': User.Role.GESTIONNAIRE,
            'password1': 'motdepasse123',
            'password2': 'motdepasse123',
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
            'password1': 'motdepasse123',
            'password2': 'motdepasse123',
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


class MembreListViewTests(TestCase):
    def test_les_comptes_coach_apparaissent_dans_la_liste(self):
        gestionnaire = creer_gestionnaire()
        coach = creer_gestionnaire(username='autre_coach')
        self.client.force_login(gestionnaire)

        response = self.client.get(reverse('accounts:membre_liste'))

        self.assertContains(response, 'autre_coach')
        self.assertContains(response, coach.get_role_display())


class MembreToggleActifViewTests(TestCase):
    def test_un_gestionnaire_peut_desactiver_un_compte_coach(self):
        gestionnaire = creer_gestionnaire()
        coach = creer_gestionnaire(username='coach_a_desactiver')
        self.client.force_login(gestionnaire)

        self.client.post(reverse('accounts:membre_toggle_actif', args=[coach.pk]))

        coach.refresh_from_db()
        self.assertFalse(coach.is_active)


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
