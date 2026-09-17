from django.db import migrations

OFFERTES_PAR_NOM = {
    '1 séance': 0,
    '10 séances + 1 offerte': 1,
    '20 séances + 3 offertes': 3,
    '25 séances + 5 offertes': 5,
}


def renseigner_offertes(apps, schema_editor):
    Offre = apps.get_model('offers', 'Offre')
    for nom, nb_offertes in OFFERTES_PAR_NOM.items():
        Offre.objects.filter(nom=nom).update(nombre_seances_offertes=nb_offertes)


def inverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('offers', '0004_offre_nombre_seances_offertes'),
    ]

    operations = [
        migrations.RunPython(renseigner_offertes, inverse_noop),
    ]
