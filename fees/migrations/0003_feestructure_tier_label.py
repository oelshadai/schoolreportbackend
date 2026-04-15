from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fees', '0002_fee_enhancements'),
    ]

    operations = [
        migrations.AddField(
            model_name='feestructure',
            name='tier_label',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Optional tier name (e.g. Bus Users, Non-Bus Users). Leave empty for all students.',
                max_length=100,
            ),
        ),
        migrations.AlterUniqueTogether(
            name='feestructure',
            unique_together={('school', 'fee_type', 'level', 'tier_label')},
        ),
        migrations.AlterModelOptions(
            name='feestructure',
            options={'ordering': ['fee_type', 'level', 'tier_label']},
        ),
    ]
