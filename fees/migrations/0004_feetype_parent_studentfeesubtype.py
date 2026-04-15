from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('fees', '0003_feestructure_tier_label'),
        ('schools', '0001_initial'),
        ('students', '0001_initial'),
    ]

    operations = [
        # Add parent_fee_type to FeeType (self-referential, nullable)
        migrations.AddField(
            model_name='feetype',
            name='parent_fee_type',
            field=models.ForeignKey(
                blank=True,
                help_text='If set, this is a sub-fee type under the parent fee type.',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='sub_types',
                to='fees.feetype',
            ),
        ),
        # Create StudentFeeSubType model
        migrations.CreateModel(
            name='StudentFeeSubType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='fee_sub_type_assignments',
                    to='students.student',
                )),
                ('main_fee_type', models.ForeignKey(
                    help_text='The top-level (parent) fee type.',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='student_sub_assignments',
                    to='fees.feetype',
                )),
                ('sub_fee_type', models.ForeignKey(
                    blank=True,
                    help_text='The sub-fee type assigned to this student. Null = none assigned.',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='assigned_students',
                    to='fees.feetype',
                )),
                ('school', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='student_fee_sub_types',
                    to='schools.school',
                )),
            ],
            options={
                'ordering': ['student', 'main_fee_type'],
                'unique_together': {('student', 'main_fee_type')},
            },
        ),
    ]
