from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

DURATION_CHOICES = [
    ('1M', '1 mes'),
    ('3M', '3 meses'),
    ('6M', '6 meses'),
    ('1Y', '1 año'),
    ('2Y', '2 años'),
]

class User(AbstractUser):
    USER_TYPES = (
        ('MATRIZ', 'Matriz'),
        ('DISTRIBUIDOR', 'Distribuidor'),
        ('REVENDEDOR', 'Revendedor'),
        ('CLIENTE', 'Cliente'),
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='DISTRIBUIDOR')
    preferred_lang = models.CharField(max_length=5, choices=[('es', 'Español'), ('en', 'English'), ('pt', 'Português')], default='es')

    def save(self, *args, **kwargs):
        if self.user_type == 'MATRIZ':
            self.is_staff = True
            self.is_superuser = True
        else:
            self.is_staff = False
            self.is_superuser = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.user_type})"

class BaseProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100)
    phone_number = models.CharField(max_length=20, unique=True)
    company = models.CharField(max_length=100, null=True, blank=True)
    rfc = models.CharField(max_length=15, null=True, blank=True)

    street = models.CharField(max_length=125)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip = models.CharField(max_length=20)
    country = models.CharField(max_length=50)

    class Meta:
        abstract = True

    def get_full_name(self):
        return f"{self.user.first_name} {self.user.last_name}".strip()

    def get_phone_number(self):
        return f"{self.phone_number}".strip()
    
    @classmethod
    def phone_exists(cls, phone):
        from django.apps import apps
        Distribuidor = apps.get_model('SIM_Control', 'Distribuidor')
        Revendedor = apps.get_model('SIM_Control', 'Revendedor')
        Clientes = apps.get_model('SIM_Control', 'Cliente')
        return Distribuidor.objects.filter(phone_number=phone).exists() \
            or Revendedor.objects.filter(phone_number=phone).exists() \
            or Clientes.objects.filter(phone_number=phone).exists()

class Distribuidor(BaseProfile):
    pass

class Revendedor(BaseProfile):
    distribuidor = models.ForeignKey(
        Distribuidor,
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name='revendedores'
    )

class Cliente(BaseProfile):
    distribuidor = models.ForeignKey(
        Distribuidor,
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name='clientes'
    )

    revendedor = models.ForeignKey(
        Revendedor,
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name='clientes'
    )

class SimCard(models.Model):
    iccid = models.CharField(max_length=50, unique=True)
    imsi = models.CharField(max_length=50, blank=True, null=True)
    msisdn = models.CharField(max_length=50, blank=True, null=True)
    imei = models.CharField(max_length=50, blank=True, null=True)
    imei_lock = models.BooleanField(default=False)
    status = models.CharField(max_length=20)
    activation_date = models.DateTimeField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    current_quota = models.BigIntegerField(blank=True, null=True)
    quota_status = models.CharField(max_length=255, blank=True, null=True)
    current_quota_SMS = models.BigIntegerField(blank=True, null=True)
    quota_status_SMS = models.CharField(max_length=255, blank=True, null=True)
    label = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.iccid} - {self.status}"
    
class MonthlySimUsage(models.Model):
    sim = models.ForeignKey(SimCard, on_delete=models.CASCADE, related_name='monthly_usage')
    month = models.CharField(max_length=7)
    data_volume = models.FloatField()
    sms_volume = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['sim', 'month'], name='uq_monthly_usage_sim_month'),
        ]

    def __str__(self):
        return f"{self.sim.iccid} - {self.month} - Data Usage {self.data_volume}"
    
class ShippingAddress(models.Model):
    salutation = models.CharField(max_length=10, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    company = models.CharField(max_length=100, null=True, blank=True)
    street = models.CharField(max_length=255)
    house_number = models.CharField(max_length=20, null=True, blank=True)
    address_line2 = models.CharField(max_length=255, null=True, blank=True)
    zip = models.CharField(max_length=20)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Order(models.Model):
    order_number = models.BigIntegerField(unique=True)
    order_type = models.CharField(max_length=50)
    order_date = models.DateTimeField()
    order_status = models.CharField(max_length=50)
    invoice_number = models.CharField(max_length=50)
    invoice_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10)
    shipping_address = models.ForeignKey(ShippingAddress, on_delete=models.CASCADE)

    def __str__(self):
        return f"Order #{self.order_number}"

class OrderSIM(models.Model):
    iccid = models.CharField(max_length=30, unique=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='sims')

    def __str__(self):
        return self.iccid

class OrderProduct(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='products')
    product_id = models.IntegerField()
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"Product {self.product_id} x {self.quantity}"

class CommandRunLog(models.Model):
    command_name = models.CharField(max_length=100, unique=True)
    last_run = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.command_name} - {self.last_run}"

class Vehicle(models.Model):
    brand = models.CharField(max_length=50, null=True, blank=True)
    model = models.CharField(max_length=50, null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)
    color = models.CharField(max_length=50, null=True, blank=True)
    unit_number = models.CharField(max_length=50, null=True, blank=True)
    imei_gps = models.CharField(max_length=50, null=True, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="vehicle", null=True, blank=True)
    sim = models.ForeignKey(SimCard, on_delete=models.SET_NULL, null=True, blank=True)

    def get_vehicle(self):
        vehicle = '%s %s %s' % (self.brand, self.model, self.year if self.year else "")
        return vehicle.strip()

class SIMAssignation(models.Model):
    sim = models.ForeignKey(SimCard, null=True, blank=True, on_delete=models.SET_NULL, related_name='iccid_key')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    assigned_to = GenericForeignKey('content_type', 'object_id')

    last_topup_date = models.DateField(null=True, blank=True)
    topup_duration = models.CharField(max_length=2, choices=DURATION_CHOICES, null=True, blank=True)
    deactivation_date = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['sim', 'content_type', 'object_id'], name='uq_sim_assignation_target'),
        ]

    def end_topup_date(self):
        if self.last_topup_date and self.topup_duration:
            days = {
                '1M': 30, '3M': 90, '6M': 180, '1Y': 365, '2Y': 730
            }.get(self.topup_duration, 0)
            return self.last_topup_date + timezone.timedelta(days=days)
        return None

class SIMStatus(models.Model):
    sim = models.ForeignKey(SimCard, on_delete=models.CASCADE, related_name='sim_status')
    status = models.CharField(max_length=20)
    operator_name = models.CharField(max_length=100)
    country_name = models.CharField(max_length=100)
    rat_type = models.CharField(max_length=10, blank=True, null=True)
    ue_ip = models.GenericIPAddressField(blank=True, null=True)
    last_updated = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['sim'], name='uq_sim_status_sim'),
        ]

class SIMQuota(models.Model):
    QUOTAS_TYPES = (
        ('DATA', 'Data'),
        ('SMS', 'SMS'),
    )
    sim = models.ForeignKey(SimCard, on_delete=models.CASCADE, related_name='quotas')
    quota_type = models.CharField(max_length=10, choices=QUOTAS_TYPES)
    volume = models.FloatField()
    total_volume = models.FloatField()
    expiry_date = models.DateTimeField(null=True, blank=True)
    peak_throughput = models.IntegerField()
    last_volume_added = models.FloatField()
    last_status_change_date = models.DateTimeField(null=True, blank=True)
    threshold_percentage = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['sim', 'quota_type'], name='uq_sim_quota_sim_type'),
        ]

class SMSMessage(models.Model):
    sim = models.ForeignKey(SimCard, on_delete=models.CASCADE, related_name='sms_messages')
    submit_date = models.DateTimeField(null=True, blank=True)
    delivery_date = models.DateTimeField(null=True, blank=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    retry_count = models.PositiveIntegerField(default=0, null=True, blank=True)
    source_address = models.CharField(max_length=32, null=True, blank=True)
    msisdn = models.CharField(max_length=32, null=True, blank=True)
    udh = models.TextField(blank=True, null=True)
    payload = models.TextField(blank=True, null=True)
    status_id = models.PositiveIntegerField(null=True, blank=True)
    status_description = models.CharField(max_length=128, null=True, blank=True)
    sms_type_id = models.PositiveIntegerField(null=True, blank=True)
    sms_type_description = models.CharField(max_length=128, null=True, blank=True)
    source_address_type_id = models.PositiveIntegerField(null=True, blank=True)
    source_address_type_description = models.CharField(max_length=128, null=True, blank=True)

class SIMLocation(models.Model):
    sim = models.ForeignKey(SimCard, null=True, blank=True, on_delete=models.SET_NULL, related_name='location')
    sample_time = models.DateTimeField(null=True, blank=True)
    latitude = models.FloatField(default=0, null=True, blank=True)
    longitude = models.FloatField(default=0, null=True, blank=True)

class UserActionLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('ENABLE', 'Enable'),
        ('DISABLE', 'Disable'),
        ('SEND_SMS', 'Send SMS'),
        ('DELETE', 'Delete'),
        ('ASSIGN', 'Assign'),
        ('REFRESH', 'Refresh'),
        ('TOPUP', 'Topup'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
    ]

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, null=True, blank=True)
    description = models.CharField(blank=True, max_length=255)
    timestamp = models.DateTimeField()

class GlobalLimits(models.Model):
    data_limit = models.IntegerField(null=False, blank=False, default=10)
    mt_limit = models.IntegerField(null=False, blank=False, default=45)
    mo_limit = models.IntegerField(null=False, blank=False, default=30)

    def __str__(self):
        return f"{self.data_limit} - {self.mt_limit} - {self.mo_limit}"
