from django.contrib import admin

from .models import CustomerPlanPriceOverride, MembershipPlan, Subscription


@admin.register(MembershipPlan)
class MembershipPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "duration_days", "price", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("sim", "plan", "status", "start_date", "end_date", "auto_renew")
    list_filter = ("status", "auto_renew")
    search_fields = ("sim__iccid", "plan__name")


@admin.register(CustomerPlanPriceOverride)
class CustomerPlanPriceOverrideAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "adjustment_percent", "is_active", "updated_at")
    list_filter = ("is_active", "plan")
    search_fields = ("user__username", "user__first_name", "user__last_name", "user__email", "plan__name")
