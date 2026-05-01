from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('schools', '0012_school_sms_settings'),
    ]

    operations = [
        # Add sms_balance to School
        migrations.AddField(
            model_name='school',
            name='sms_balance',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Number of SMS units available (1 unit = 1 SMS sent via the platform Arkesel account)',
            ),
        ),

        # Create SmsPurchaseOrder table
        migrations.CreateModel(
            name='SmsPurchaseOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sms_units', models.PositiveIntegerField(help_text='Number of SMS credits purchased')),
                ('amount_ghs', models.DecimalField(decimal_places=2, max_digits=10, help_text='Amount paid in GHS')),
                ('status', models.CharField(
                    choices=[('pending', 'Pending Payment'), ('paid', 'Paid — Credited'), ('failed', 'Payment Failed')],
                    default='pending',
                    max_length=20,
                )),
                ('paystack_reference', models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ('credited_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('school', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='sms_purchases',
                    to='schools.school',
                )),
                ('requested_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='sms_purchase_orders',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'sms_purchase_orders',
                'ordering': ['-created_at'],
            },
        ),
    ]
