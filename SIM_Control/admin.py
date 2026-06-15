from django.contrib import admin
from .models import *

TOKEN_FIELDS = (
    "mercado_pago_access_token",
    "mercado_pago_refresh_token",
)


class MercadoPagoProfileAdmin(admin.ModelAdmin):
    exclude = TOKEN_FIELDS
    readonly_fields = (
        "mercado_pago_user_id",
        "mercado_pago_token_expires_at",
        "mercado_pago_connected_at",
        "mercado_pago_is_connected",
    )


# Register your models here.
@admin.register(SimCard)
class SimCardAdmin(admin.ModelAdmin):
    list_display = (
        'iccid', 'imsi', 'msisdn', 'gps_imei', 'imei_lock', 
        'status', 'activation_date', 'ip_address', 
        'current_quota', 'quota_status', 
        'current_quota_SMS', 'quota_status_SMS', 
        'label'
    )

    @admin.display(description="IMEI")
    def gps_imei(self, obj):
        return obj.display_imei
@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'user_type', 'email')

@admin.register(UserActionLog)
class UserActionLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp')


@admin.register(Distribuidor)
class DistribuidorAdmin(MercadoPagoProfileAdmin):
    list_display = ("first_name", "last_name", "company", "mercado_pago_is_connected", "mercado_pago_connected_at")
    search_fields = ("first_name", "last_name", "company", "email")


@admin.register(Revendedor)
class RevendedorAdmin(MercadoPagoProfileAdmin):
    list_display = ("first_name", "last_name", "company", "distribuidor", "mercado_pago_is_connected", "mercado_pago_connected_at")
    search_fields = ("first_name", "last_name", "company", "email")
