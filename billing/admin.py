from django.contrib import admin

from .models import CommissionPeriod, CustomerPlanPriceOverride, DistributorSale, MembershipPlan, Subscription, SubscriptionPurchase


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


@admin.register(SubscriptionPurchase)
class SubscriptionPurchaseAdmin(admin.ModelAdmin):
    list_display = ("reference", "user", "sim", "plan", "status", "amount", "mp_account_type", "mp_payment_id")
    list_filter = ("status", "mp_account_type", "currency")
    search_fields = ("reference", "user__email", "sim__iccid", "mp_payment_id", "mp_preference_id")


@admin.register(DistributorSale)
class DistributorSaleAdmin(admin.ModelAdmin):
    list_display = ("payment_id", "distribuidor", "revendedor", "cliente", "plan", "amount", "status", "period")
    list_filter = ("status", "period", "plan")
    search_fields = ("payment_id", "cliente__email", "distribuidor__company", "revendedor__company")


@admin.register(CommissionPeriod)
class CommissionPeriodAdmin(admin.ModelAdmin):
    list_display = (
        "period_label",
        "distribuidor",
        "revendedor",
        "total_vendido",
        "renewal_count",
        "comision_calculada",
        "status",
        "paid_at",
        "marked_by",
    )
    list_filter = ("status", "year", "month")
    search_fields = ("distribuidor__company", "revendedor__company", "distribuidor__email", "revendedor__email")
