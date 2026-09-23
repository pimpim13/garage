from django import forms

from .models import Actualite


class ActualiteForm(forms.ModelForm):
    class Meta:
        model = Actualite
        fields = ['texte', 'date_debut', 'date_fin', 'cible']
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'date_fin': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }
