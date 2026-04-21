from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fees', '0004_feetype_parent_studentfeesubtype'),
    ]

    operations = [
        migrations.AddField(
            model_name='feepayment',
            name='attendance_date',
            field=models.DateField(
                blank=True,
                null=True,
                help_text='For daily fees auto-recorded from attendance; the school day this covers.',
            ),
        ),
        migrations.AddConstraint(
            model_name='feepayment',
            constraint=models.UniqueConstraint(
                fields=['student', 'fee_type', 'attendance_date'],
                condition=models.Q(attendance_date__isnull=False),
                name='unique_daily_fee_per_student_per_day',
            ),
        ),
    ]
