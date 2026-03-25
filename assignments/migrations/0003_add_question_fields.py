# Generated migration to add missing Question fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assignments', '0002_add_missing_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='max_files',
            field=models.IntegerField(default=5, help_text='Maximum number of files allowed'),
        ),
    ]
