from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
	ordering = ("-date_joined",)
	list_display = ("email", "first_name", "last_name", "role", "school", "is_active", "is_staff")
	list_filter = ("role", "is_active", "is_staff")
	search_fields = ("email", "first_name", "last_name")

	fieldsets = (
		(None, {"fields": ("email", "password")}),
		(_("Personal info"), {"fields": ("first_name", "last_name", "phone_number", "profile_picture")}),
		(_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
		(_("Important dates"), {"fields": ("last_login", "date_joined")}),
		(_("School & Role"), {"fields": ("role", "school")}),
	)

	add_fieldsets = (
		(None, {"classes": ("wide",), "fields": ("email", "first_name", "last_name", "role", "school", "password1", "password2")}),
	)

	filter_horizontal = ("groups", "user_permissions")
	readonly_fields = ("last_login", "date_joined")

	# Use email as username
	add_form_template = None
	list_display_links = ("email",)

	def get_fieldsets(self, request, obj=None):
		return super().get_fieldsets(request, obj)
