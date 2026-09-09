from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User

ROLES_ASSIGNABLES = [User.Role.MEMBRE, User.Role.GESTIONNAIRE]

MEMBRE_FIELDS = [
    'username', 'first_name', 'last_name', 'role', 'email', 'telephone', 'famille', 'tolerance_seances_negatives',
]
MEMBRE_LABELS = {
    'role': 'Rôle',
    'tolerance_seances_negatives': 'Tolérance de séances négatives',
}


class RoleAssignableMixin(forms.ModelForm):
    role = forms.ChoiceField(choices=[(r.value, r.label) for r in ROLES_ASSIGNABLES], label='Rôle')


class MembreCreateForm(RoleAssignableMixin, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = MEMBRE_FIELDS
        labels = MEMBRE_LABELS


class MembreUpdateForm(RoleAssignableMixin):
    class Meta:
        model = User
        fields = MEMBRE_FIELDS
        labels = MEMBRE_LABELS
