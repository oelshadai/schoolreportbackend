from django.contrib import admin
from .models import SubscriptionPlan, Subscription, Payment


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
	list_display = ("name", "plan_type", "price", "duration_days", "is_active")
	list_filter = ("plan_type", "is_active")
	search_fields = ("name",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
	list_display = ("school", "plan", "start_date", "end_date", "status", "auto_renew")
	list_filter = ("status", "auto_renew", "plan")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
	list_display = ("school", "amount", "payment_method", "status", "transaction_id", "payment_date")
	list_filter = ("payment_method", "status")
	search_fields = ("transaction_id", "reference")
