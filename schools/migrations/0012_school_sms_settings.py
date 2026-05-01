from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0011_add_teachers_can_add_students'),
    ]

    operations = [
        migrations.AddField(
            model_name='school',
            name='sms_enabled',
            field=models.BooleanField(default=False, help_text='Master switch — enable SMS notifications for this school'),
        ),
        migrations.AddField(
            model_name='school',
            name='arkesel_api_key',
            field=models.CharField(blank=True, help_text='Arkesel API key from your Arkesel dashboard', max_length=200),
        ),
        migrations.AddField(
            model_name='school',
            name='sms_sender_name',
            field=models.CharField(blank=True, default='SchoolSMS', help_text='SMS sender ID (max 11 alphanumeric chars)', max_length=11),
        ),
        migrations.AddField(
            model_name='school',
            name='sms_attendance_enabled',
            field=models.BooleanField(default=False, help_text='Send SMS to parents/guardians when attendance is taken'),
        ),
        migrations.AddField(
            model_name='school',
            name='sms_fee_reminder_enabled',
            field=models.BooleanField(default=False, help_text='Allow admins to send fee-reminder SMS to parents of students with unpaid bills'),
        ),
    ]
