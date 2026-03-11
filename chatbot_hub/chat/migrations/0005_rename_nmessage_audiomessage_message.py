# Generated migration to rename nmessage to message in AudioMessage model

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0004_audiomessage'),
    ]

    operations = [
        migrations.RenameField(
            model_name='audiomessage',
            old_name='nmessage',
            new_name='message',
        ),
    ]
