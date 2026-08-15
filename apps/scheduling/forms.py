from django import forms

from apps.accounts.models import User

from .models import ModeleSeance, Seance


class SeanceForm(forms.ModelForm):
    modele = forms.ModelChoiceField(
        queryset=ModeleSeance.objects.all(),
        required=False,
        label="Séance type (facultatif)",
        help_text="Sélectionner une séance type pré-remplit les champs ci-dessous, qui restent modifiables.",
    )

    class Meta:
        model = Seance
        fields = ['modele', 'nom', 'debut', 'duree_minutes', 'capacite_max', 'coach', 'delai_annulation_heures']
        widgets = {
            'debut': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }
        labels = {
            'nom': 'Titre de la séance',
            'debut': 'Date et heure de début',
            'duree_minutes': 'Durée (minutes)',
            'capacite_max': 'Nombre maximum de participants',
            'delai_annulation_heures': "Délai d'annulation (heures)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['debut'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['coach'].queryset = User.objects.filter(
            role__in=[User.Role.ADMIN, User.Role.GESTIONNAIRE]
        ).order_by('first_name', 'username')


class ModeleSeanceForm(forms.ModelForm):
    class Meta:
        model = ModeleSeance
        fields = ['nom', 'duree_minutes', 'capacite_max_defaut', 'delai_annulation_defaut_heures', 'description']
        labels = {
            'duree_minutes': 'Durée (minutes)',
            'capacite_max_defaut': 'Nombre maximum de participants par défaut',
            'delai_annulation_defaut_heures': "Délai d'annulation par défaut (heures)",
        }
