from django.db import migrations, models


def convertir_booleen_en_mode(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(email_ouverture_seance=False).update(mode_email_ouverture='aucun')


def convertir_mode_en_booleen(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(mode_email_ouverture='aucun').update(email_ouverture_seance=False)
    User.objects.exclude(mode_email_ouverture='aucun').update(email_ouverture_seance=True)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_user_email_annulation_seance'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='mode_email_ouverture',
            field=models.CharField(
                choices=[('seance', 'Un email par séance'), ('recap', 'Un récapitulatif par jour'), ('aucun', 'Aucun email')],
                default='seance',
                help_text="Un email par séance ouverte, un seul récapitulatif quotidien (envoyé à 21h avec l'ouverture des inscriptions), ou aucun email. Le mot de passe oublié est envoyé quoi qu'il arrive, indépendamment de ce réglage.",
                max_length=10,
                verbose_name="email à l'ouverture des inscriptions",
            ),
        ),
        migrations.RunPython(convertir_booleen_en_mode, convertir_mode_en_booleen),
        migrations.RemoveField(model_name='user', name='email_ouverture_seance'),
    ]
