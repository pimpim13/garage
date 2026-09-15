from django.db import migrations

OFFRES = [
    {
        'nom': '1 séance',
        'prix': 10,
        'nombre_seances': 1,
        'duree_validite_mois': None,
        'description': "Achat à l'unité, sans prolongation de la durée de validité du solde.",
    },
    {
        'nom': '10 séances + 1 offerte',
        'prix': 100,
        'nombre_seances': 11,
        'duree_validite_mois': 3,
        'description': '',
    },
    {
        'nom': '20 séances + 3 offertes',
        'prix': 200,
        'nombre_seances': 23,
        'duree_validite_mois': 6,
        'description': '',
    },
    {
        'nom': '25 séances + 5 offertes',
        'prix': 250,
        'nombre_seances': 30,
        'duree_validite_mois': 6,
        'description': '',
    },
]


def creer_offres(apps, schema_editor):
    Offre = apps.get_model('offers', 'Offre')
    for donnees in OFFRES:
        Offre.objects.get_or_create(
            nom=donnees['nom'],
            defaults={
                'type_offre': 'carnet',
                'prix': donnees['prix'],
                'nombre_seances': donnees['nombre_seances'],
                'duree_validite_mois': donnees['duree_validite_mois'],
                'description': donnees['description'],
                'active': True,
            },
        )


def inverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('offers', '0002_offre_duree_validite_mois'),
    ]

    operations = [
        migrations.RunPython(creer_offres, inverse_noop),
    ]
