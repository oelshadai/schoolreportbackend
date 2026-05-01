from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fees', '0005_feepayment_attendance_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='feepayment',
            name='paystack_reference',
            field=models.CharField(
                blank=True,
                help_text='Paystack transaction reference for online payments',
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name='feepayment',
            name='paystack_status',
            field=models.CharField(
                blank=True,
                choices=[('pending', 'Pending'), ('success', 'Success'), ('failed', 'Failed')],
                help_text='Status of Paystack transaction',
                max_length=20,
            ),
        ),
    ]
