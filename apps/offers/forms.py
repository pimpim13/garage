from django import forms

from .models import Offre


class OffreForm(forms.ModelForm):
    class Meta:
        model = Offre
        fields = ['nom', 'type_offre', 'description', 'prix', 'nombre_seances', 'duree_validite_mois', 'active']
        labels = {
            'nom': 'Nom',
            'type_offre': "Type d'offre",
            'prix': 'Prix (€)',
            'nombre_seances': 'Nombre de séances',
            'duree_validite_mois': 'Durée de validité (mois)',
            'active': 'Active',
        }
        help_texts = {
            'duree_validite_mois': "Laisser vide pour un achat à l'unité qui ne prolonge pas la validité du solde.",
        }
