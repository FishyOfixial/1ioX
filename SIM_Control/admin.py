from django.contrib import admin
from .models import *

# Register your models here.
@admin.register(SimCard)
class SimCardAdmin(admin.ModelAdmin):
    list_display = (
        'iccid', 'imsi', 'msisdn', 'imei', 'imei_lock', 
        'status', 'activation_date', 'ip_address', 
        'current_quota', 'quota_status', 
        'current_quota_SMS', 'quota_status_SMS', 
        'label'
    )

@admin.register(MonthlySimUsage)
class MonthlySimUsageAdmin(admin.ModelAdmin):
    list_display = ('iccid', 'month', 'data_volume', 'sms_volume', 'created_at')

@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'user_type', 'email')