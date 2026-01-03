# Generated migration for timed tasks

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0003_dailyattendance'),
        ('schools', '0005_school_show_promotion_on_terminal_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('assignments', '0003_question_case_sensitive_question_expected_answer'),
    ]

    operations = [
        migrations.CreateModel(
            name='TimedTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('start_time', models.DateTimeField(help_text='When students can start the task')),
                ('duration', models.IntegerField(help_text='Duration in minutes')),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('SCHEDULED', 'Scheduled'), ('ACTIVE', 'Active'), ('COMPLETED', 'Completed')], default='DRAFT', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('class_instance', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='schools.class')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'timed_tasks',
            },
        ),
        migrations.CreateModel(
            name='TaskQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question_text', models.TextField()),
                ('option_a', models.CharField(max_length=500)),
                ('option_b', models.CharField(max_length=500)),
                ('option_c', models.CharField(max_length=500)),
                ('option_d', models.CharField(max_length=500)),
                ('correct_answer', models.IntegerField(choices=[(0, 'A'), (1, 'B'), (2, 'C'), (3, 'D')])),
                ('order', models.IntegerField(default=0)),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='assignments.timedtask')),
            ],
            options={
                'db_table': 'task_questions',
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='TaskAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('time_taken', models.IntegerField(blank=True, help_text='Time taken in seconds', null=True)),
                ('score', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('status', models.CharField(choices=[('IN_PROGRESS', 'In Progress'), ('SUBMITTED', 'Submitted'), ('AUTO_SUBMITTED', 'Auto Submitted'), ('EXPIRED', 'Expired')], default='IN_PROGRESS', max_length=20)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='task_attempts', to='students.student')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attempts', to='assignments.timedtask')),
            ],
            options={
                'db_table': 'task_attempts',
            },
        ),
        migrations.CreateModel(
            name='TaskAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('selected_option', models.IntegerField(choices=[(0, 'A'), (1, 'B'), (2, 'C'), (3, 'D')])),
                ('is_correct', models.BooleanField(default=False)),
                ('answered_at', models.DateTimeField(auto_now_add=True)),
                ('attempt', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='assignments.taskattempt')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='assignments.taskquestion')),
            ],
            options={
                'db_table': 'task_answers',
            },
        ),
        migrations.AddConstraint(
            model_name='taskattempt',
            constraint=models.UniqueConstraint(fields=('task', 'student'), name='unique_task_student'),
        ),
        migrations.AddConstraint(
            model_name='taskanswer',
            constraint=models.UniqueConstraint(fields=('attempt', 'question'), name='unique_attempt_question'),
        ),
    ]