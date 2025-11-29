from django.db import models
from schools.models import School


class SubscriptionPlan(models.Model):
    """Subscription Plan Model"""
    
    PLAN_TYPE_CHOICES = [
        ('TERM', 'Per Term'),
        ('YEARLY', 'Yearly'),
        ('PER_STUDENT', 'Per Student'),
    ]
    
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES)
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
        return f"{self.name} - GH₵{self.price}"


class Subscription(models.Model):
    """School Subscription Model"""
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('EXPIRED', 'Expired'),
        ('CANCELLED', 'Cancelled'),
        ('SUSPENDED', 'Suspended'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    
    auto_renew = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subscriptions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.school.name} - {self.plan.name} - {self.status}"
    
    def is_valid(self):
        """Check if subscription is still valid"""
        from datetime import date
        return self.status == 'ACTIVE' and self.end_date >= date.today()


class Payment(models.Model):
    """Payment Model"""
    
    PAYMENT_METHOD_CHOICES = [
        ('MOBILE_MONEY', 'Mobile Money'),
        ('PAYSTACK', 'Paystack'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CASH', 'Cash'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='payments')
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Payment Gateway Details
    transaction_id = models.CharField(max_length=255, unique=True)
    reference = models.CharField(max_length=255, blank=True)
    
    # Metadata
    payment_date = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.school.name} - GH₵{self.amount} - {self.status}"
