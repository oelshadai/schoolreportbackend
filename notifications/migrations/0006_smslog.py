from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('notifications', '0005_supportticket'),
        ('schools', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SmsLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sms_type', models.CharField(
                    choices=[('fee_reminder', 'Fee Reminder'), ('attendance', 'Attendance Alert'), ('general', 'General')],
                    default='general', max_length=30,
                )),
                ('status', models.CharField(
                    choices=[('success', 'Success'), ('partial', 'Partial'), ('failed', 'Failed'), ('pending', 'Pending')],
                    default='pending', max_length=20,
                )),
                ('total_recipients', models.IntegerField(default=0)),
                ('sent_count', models.IntegerField(default=0)),
                ('failed_count', models.IntegerField(default=0)),
                ('no_phone_count', models.IntegerField(default=0)),
                ('message_preview', models.TextField(blank=True)),
                ('filters_used', models.JSONField(blank=True, default=dict)),
                ('details', models.JSONField(blank=True, default=list)),
                ('failure_reason', models.CharField(blank=True, max_length=300)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('school', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='sms_logs',
                    to='schools.school',
                )),
                ('sent_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='sms_logs_sent',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'sms_logs',
                'ordering': ['-created_at'],
            },
        ),
    ]
