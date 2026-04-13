# Data repair migration: fix classes where class_teacher_id was accidentally stored
# as the Teacher model PK instead of the User model PK.
# This happens when ClassesManagement.tsx sends t.id (Teacher PK) instead of t.user_id.

from django.db import migrations
import logging

logger = logging.getLogger(__name__)


def fix_class_teacher_ids(apps, schema_editor):
    """
    For each Class whose class_teacher_id does NOT resolve to a User with role='TEACHER',
    check if class_teacher_id happens to equal some Teacher.pk.
    If so, replace it with that Teacher's user_id (the correct FK target).
    """
    Class = apps.get_model('schools', 'Class')
    Teacher = apps.get_model('teachers', 'Teacher')
    User = apps.get_model('accounts', 'User')

    fixed = 0
    for cls in Class.objects.filter(class_teacher__isnull=False):
        # Is the current class_teacher_id a valid User with TEACHER role?
        is_valid = User.objects.filter(
            pk=cls.class_teacher_id,
            role='TEACHER'
        ).exists()

        if is_valid:
            continue  # nothing to fix

        # Not a valid teacher user — check if it's a Teacher model PK
        try:
            teacher_profile = Teacher.objects.get(pk=cls.class_teacher_id)
            correct_user_id = teacher_profile.user_id

            # Sanity check: the correct user should exist and be a teacher
            if User.objects.filter(pk=correct_user_id, role='TEACHER').exists():
                old_id = cls.class_teacher_id
                cls.class_teacher_id = correct_user_id
                cls.save(update_fields=['class_teacher_id'])
                fixed += 1
                logger.info(
                    f"Fixed Class {cls.id}: class_teacher_id {old_id} -> {correct_user_id}"
                )
        except Teacher.DoesNotExist:
            # class_teacher_id matches neither a Teacher user nor a Teacher object  
            logger.warning(
                f"Class {cls.id}: class_teacher_id={cls.class_teacher_id} "
                f"could not be resolved to a valid Teacher — skipped"
            )

    logger.info(f"Data repair: fixed {fixed} class(es)")


def reverse_fix(apps, schema_editor):
    # Reversal is a no-op: restoring the old (wrong) IDs would break things again
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0008_parent_portal_settings'),
        ('teachers', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_class_teacher_ids, reverse_fix),
    ]
