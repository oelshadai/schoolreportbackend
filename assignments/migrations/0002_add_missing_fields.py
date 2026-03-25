# Generated migration to add missing fields to StudentAssignment

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assignments', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentassignment',
            name='current_attempt_started_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='studentassignment',
            name='is_locked',
            field=models.BooleanField(default=False, help_text='Locked during timed attempts'),
        ),
    ]