from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User

MEMBRE_FIELDS = ['username', 'first_name', 'last_name', 'email', 'telephone', 'famille', 'tolerance_seances_negatives']
MEMBRE_LABELS = {
    'tolerance_seances_negatives': 'Tolérance de séances négatives',
}


class MembreCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = MEMBRE_FIELDS
        labels = MEMBRE_LABELS

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.MEMBRE
        if commit:
            user.save()
        return user


class MembreUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = MEMBRE_FIELDS
        labels = MEMBRE_LABELS
