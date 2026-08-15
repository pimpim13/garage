from django.contrib.auth.forms import UserCreationForm

from .models import User


class MembreCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'first_name', 'last_name', 'telephone', 'tolerance_seances_negatives']
        labels = {
            'tolerance_seances_negatives': 'Tolérance de séances négatives',
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.MEMBRE
        if commit:
            user.save()
        return user
