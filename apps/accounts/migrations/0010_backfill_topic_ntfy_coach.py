import secrets

from django.db import migrations

ROLES_ANIMATEURS = ['admin', 'gestionnaire', 'coach']


def generer_topics(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    topics_existants = set(
        User.objects.exclude(topic_ntfy_coach__isnull=True).values_list('topic_ntfy_coach', flat=True)
    )
    a_completer = User.objects.filter(role__in=ROLES_ANIMATEURS, topic_ntfy_coach__isnull=True)
    for user in a_completer:
        while True:
            candidat = f"garage-coach-{secrets.token_hex(4)}"
            if candidat not in topics_existants:
                topics_existants.add(candidat)
                break
        user.topic_ntfy_coach = candidat
        user.save(update_fields=['topic_ntfy_coach'])


def inverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_user_topic_ntfy_coach'),
    ]

    operations = [
        migrations.RunPython(generer_topics, inverse_noop),
    ]
