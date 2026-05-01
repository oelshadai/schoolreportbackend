from django.db import models
from django.utils import timezone
from datetime import timedelta, date


# ---------------------------------------------------------------------------
# Plan constants – single source of truth for the whole codebase
# ---------------------------------------------------------------------------
PLAN_FREE = 'FREE'
PLAN_MONTHLY = 'MONTHLY'
PLAN_YEARLY = 'YEARLY'

PLAN_CHOICES = [
    (PLAN_FREE,    'Free Trial (14 days)'),
    (PLAN_MONTHLY, 'Monthly – KES 400/month'),
    (PLAN_YEARLY,  'Yearly – KES 4,400/year (1 month free)'),
]

PLAN_PRICES = {
    PLAN_FREE:    0,
    PLAN_MONTHLY: 400,
    PLAN_YEARLY:  4400,   # 11 × 400
}

PLAN_DURATIONS = {
    PLAN_FREE:    14,   # days (trial)
    PLAN_MONTHLY: 30,
    PLAN_YEARLY:  366,  # ~12 months
}


class SubscriptionPlan(models.Model):
    """Subscription Plan Model"""

    PLAN_TYPE_CHOICES = PLAN_CHOICES

    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES, default=PLAN_FREE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.IntegerField(help_text="Duration in days")
    max_students = models.IntegerField(null=True, blank=True, help_text="Max students allowed (null = unlimited)")
    max_teachers = models.IntegerField(null=True, blank=True, help_text="Max teachers allowed (null = unlimited)")

    # Features
    bulk_upload = models.BooleanField(default=True)
    pdf_generation = models.BooleanField(default=True)
    custom_branding = models.BooleanField(default=True)
    analytics = models.BooleanField(default=True)
    support_level = models.CharField(max_length=50, default='Standard')

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'subscription_plans'
        ordering = ['price']

    def __str__(self):
        return f"{self.name} – KES {self.price}"


class Subscription(models.Model):
    """Active subscription record for a school."""

    STATUS_ACTIVE    = 'ACTIVE'
    STATUS_EXPIRED   = 'EXPIRED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_LOCKED    = 'LOCKED'

    STATUS_CHOICES = [
        (STATUS_ACTIVE,    'Active'),
        (STATUS_EXPIRED,   'Expired'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_LOCKED,    'Locked (trial ended)'),
    ]

    school      = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='subscriptions')
    plan_type   = models.CharField(max_length=20, choices=PLAN_CHOICES, default=PLAN_FREE)
    start_date  = models.DateField()
    end_date    = models.DateField()
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    auto_renew  = models.BooleanField(default=False)

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subscriptions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.school.name} – {self.plan_type} – {self.status}"

    def is_valid(self):
        """Return True if the subscription is active and has not expired."""
        return self.status == self.STATUS_ACTIVE and self.end_date >= date.today()

    def days_remaining(self):
        delta = (self.end_date - date.today()).days
        return max(delta, 0)

    @classmethod
    def create_for_school(cls, school, plan_type: str) -> 'Subscription':
        """Create a fresh subscription for *school* with the given plan."""
        today = date.today()
        duration = PLAN_DURATIONS.get(plan_type, PLAN_DURATIONS[PLAN_FREE])
        return cls.objects.create(
            school=school,
            plan_type=plan_type,
            start_date=today,
            end_date=today + timedelta(days=duration),
            status=cls.STATUS_ACTIVE,
        )


class Payment(models.Model):
    """Payment record for a subscription upgrade."""

    METHOD_MOBILE = 'MOBILE_MONEY'
    METHOD_BANK   = 'BANK_TRANSFER'
    METHOD_CASH   = 'CASH'

    PAYMENT_METHOD_CHOICES = [
        (METHOD_MOBILE, 'Mobile Money'),
        (METHOD_BANK,   'Bank Transfer'),
        (METHOD_CASH,   'Cash'),
    ]

    STATUS_PENDING   = 'PENDING'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_FAILED    = 'FAILED'

    STATUS_CHOICES = [
        (STATUS_PENDING,   'Pending'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED,    'Failed'),
        ('REFUNDED',       'Refunded'),
    ]

    school         = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='payments')
    subscription   = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    plan_type      = models.CharField(max_length=20, choices=PLAN_CHOICES, default=PLAN_MONTHLY)

    amount         = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    transaction_id = models.CharField(max_length=255, unique=True)
    reference      = models.CharField(max_length=255, blank=True)

    payment_date   = models.DateTimeField(null=True, blank=True)
    remarks        = models.TextField(blank=True)

    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.school.name} – KES {self.amount} – {self.status}"
