import threading
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from .models import (
    Staff, StaffSalary, PayrollRecord, Income, Expense,
    Budget, BudgetItem, ExpenseApproval, PaymentReminder, FinancialAuditLog
)

_audit_context = threading.local()


def set_audit_context(user=None, action=None, extra_data=None, notes=None):
    _audit_context.user = user
    _audit_context.action = action
    _audit_context.extra_data = extra_data or {}
    _audit_context.notes = notes or ''


def get_audit_context():
    return {
        'user': getattr(_audit_context, 'user', None),
        'action': getattr(_audit_context, 'action', None),
        'extra_data': getattr(_audit_context, 'extra_data', {}),
        'notes': getattr(_audit_context, 'notes', ''),
    }


def clear_audit_context():
    _audit_context.user = None
    _audit_context.action = None
    _audit_context.extra_data = {}
    _audit_context.notes = ''


audited_models = [
    Staff, StaffSalary, PayrollRecord, Income, Expense,
    Budget, BudgetItem, ExpenseApproval, PaymentReminder
]


def _serialize_instance(instance):
    return FinancialAuditLog.serialize_instance(instance)


def _get_changes(instance, created):
    old_data = getattr(instance, '_audit_old_snapshot', {}) or {}
    new_data = _serialize_instance(instance)
    if created:
        return new_data
    return FinancialAuditLog.compute_changes(old_data, new_data)


def _log_instance_action(instance, created=False, action=None):
    if getattr(instance, '_audit_skip_signals', False):
        return

    context = get_audit_context()
    computed_action = context['action'] or ('CREATE' if created else 'UPDATE')
    if action:
        computed_action = action

    FinancialAuditLog.log_action(
        instance=instance,
        user=context['user'],
        action=computed_action,
        changes=_get_changes(instance, created),
        extra_data=context['extra_data'],
        notes=context['notes'],
    )


@receiver(pre_save, sender=Staff)
@receiver(pre_save, sender=StaffSalary)
@receiver(pre_save, sender=PayrollRecord)
@receiver(pre_save, sender=Income)
@receiver(pre_save, sender=Expense)
@receiver(pre_save, sender=Budget)
@receiver(pre_save, sender=BudgetItem)
@receiver(pre_save, sender=ExpenseApproval)
@receiver(pre_save, sender=PaymentReminder)
def capture_pre_save_snapshot(sender, instance, **kwargs):
    if getattr(instance, '_audit_skip_signals', False):
        return

    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._audit_old_snapshot = _serialize_instance(old_instance)
        except sender.DoesNotExist:
            instance._audit_old_snapshot = {}
    else:
        instance._audit_old_snapshot = {}


@receiver(post_save, sender=Staff)
@receiver(post_save, sender=StaffSalary)
@receiver(post_save, sender=PayrollRecord)
@receiver(post_save, sender=Income)
@receiver(post_save, sender=Expense)
@receiver(post_save, sender=Budget)
@receiver(post_save, sender=BudgetItem)
@receiver(post_save, sender=ExpenseApproval)
@receiver(post_save, sender=PaymentReminder)
def log_post_save(sender, instance, created, **kwargs):
    if getattr(instance, '_audit_skip_signals', False):
        return
    _log_instance_action(instance, created=created)


@receiver(post_delete, sender=Staff)
@receiver(post_delete, sender=StaffSalary)
@receiver(post_delete, sender=PayrollRecord)
@receiver(post_delete, sender=Income)
@receiver(post_delete, sender=Expense)
@receiver(post_delete, sender=Budget)
@receiver(post_delete, sender=BudgetItem)
@receiver(post_delete, sender=ExpenseApproval)
@receiver(post_delete, sender=PaymentReminder)
def log_post_delete(sender, instance, **kwargs):
    if getattr(instance, '_audit_skip_signals', False):
        return
    context = get_audit_context()
    FinancialAuditLog.log_action(
        instance=instance,
        user=context['user'],
        action='DELETE',
        changes=_serialize_instance(instance),
        extra_data=context['extra_data'],
        notes=context['notes'],
    )
