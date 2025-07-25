from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

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
        ('FINAL', 'Usuario Final'),
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='DISTRIBUIDOR')

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
    iccid = models.CharField(max_length=30)
    month = models.CharField(max_length=7)
    data_volume = models.FloatField()
    sms_volume = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.iccid} - {self.month} - Data Usage {self.data_volume}"
    
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
    
class Distribuidor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=20, unique=True)
    rfc = models.CharField(max_length=15)
    company = models.CharField(max_length=100)
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip = models.CharField(max_length=20)
    country = models.CharField(max_length=10)

    def get_full_name(self):
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

class Revendedor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=20, unique=True)
    rfc = models.CharField(max_length=15)
    company = models.CharField(max_length=100)
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip = models.CharField(max_length=20)
    country = models.CharField(max_length=10)
    distribuidor = models.ForeignKey(Distribuidor, null=True, blank=True, on_delete=models.CASCADE, related_name='revendedor')

    def get_full_name(self):
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

class UsuarioFinal(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100, unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=20, unique=True)
    company = models.CharField(max_length=100, null=True, blank=True)
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip = models.CharField(max_length=20)
    country = models.CharField(max_length=10)
    distribuidor = models.ForeignKey(Distribuidor, null=True, blank=True, on_delete=models.CASCADE, related_name='usuarios_finales')
    revendedor = models.ForeignKey(Revendedor, null=True, blank=True, on_delete=models.CASCADE, related_name='usuarios_finales')

    def get_full_name(self):
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()
    
    def get_phone_number(self):
        phone_number = '%s' % (self.phone_number)
        return phone_number.strip()

class Vehicle(models.Model):
    brand = models.CharField(max_length=50, null=True, blank=True)
    model = models.CharField(max_length=50, null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)
    color = models.CharField(max_length=50, null=True, blank=True)
    unit_number = models.CharField(max_length=50, null=True, blank=True)
    imei_gps = models.CharField(max_length=50, null=True, blank=True)
    usuario = models.ForeignKey(UsuarioFinal, on_delete=models.CASCADE, related_name="vehicle", null=True, blank=True)
    sim = models.ForeignKey(SimCard, on_delete=models.SET_NULL, null=True, blank=True)
    def get_vehicle(self):
        vehicle = '%s %s %s' % (self.brand, self.model, self.year if self.year else "")
        return vehicle.strip()

class SIMAssignation(models.Model):
    iccid = models.ForeignKey(SimCard, null=True, blank=True, on_delete=models.SET_NULL, related_name='iccid_key')
    assigned_to_distribuidor = models.ForeignKey(Distribuidor, null=True, blank=True, on_delete=models.SET_NULL, related_name='distribuidor')
    assigned_to_revendedor = models.ForeignKey(Revendedor, null=True, blank=True, on_delete=models.SET_NULL, related_name='revendedor')
    assigned_to_usuario_final = models.ForeignKey(UsuarioFinal, null=True, blank=True, on_delete=models.SET_NULL, related_name='usuario_final')
    assigned_to_vehicle = models.OneToOneField(Vehicle, null=True, blank=True, on_delete=models.SET_NULL, related_name='vehiculo')
    last_topup_date = models.DateField(null=True, blank=True)
    topup_duration = models.CharField(max_length=2, choices=DURATION_CHOICES, null=True, blank=True)
    deactivation_date = models.DateField(null=True, blank=True)

    def end_topup_date(self):
        if self.last_topup_date and self.topup_duration:
            duracion = self.topup_duration
            if duracion == '1M':
                return self.last_topup_date + timezone.timedelta(days=30)
            elif duracion == '3M':
                return self.last_topup_date + timezone.timedelta(days=90)
            elif duracion == '6M':
                return self.last_topup_date + timezone.timedelta(days=180)
            elif duracion == '1Y':
                return self.last_topup_date + timezone.timedelta(days=365)
            elif duracion == '2Y':
                return self.last_topup_date + timezone.timedelta(days=730)
        return None

class SIMStatus(models.Model):
    iccid = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20)
    operator_name = models.CharField(max_length=100)
    country_name = models.CharField(max_length=100)
    rat_type = models.CharField(max_length=10, blank=True, null=True)
    ue_ip = models.GenericIPAddressField(blank=True, null=True)
    last_updated = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.iccid} - {self.status}"

class SIMQuota(models.Model):
    iccid = models.CharField(max_length=20, unique=True)
    volume = models.FloatField()
    total_volume = models.FloatField()
    expiry_date = models.DateTimeField(null=True, blank=True)
    peak_throughput = models.IntegerField()
    last_volume_added = models.FloatField()
    last_status_change_date = models.DateTimeField(null=True, blank=True)
    threshold_percentage = models.IntegerField()

    def __str__(self):
        return f"{self.iccid} ({self.volume} / {self.total_volume} MB)"

class SIMSMSQuota(models.Model):
    iccid = models.CharField(max_length=20, unique=True)
    volume = models.FloatField()
    total_volume = models.FloatField()
    expiry_date = models.DateTimeField(null=True, blank=True)
    peak_throughput = models.IntegerField()
    last_volume_added = models.FloatField()
    last_status_change_date = models.DateTimeField(null=True, blank=True)
    threshold_percentage = models.IntegerField()

    def __str__(self):
        return f"{self.iccid} ({self.volume} / {self.total_volume} SMS)"
    
class SMSMessage(models.Model):
    iccid = models.CharField(max_length=32)
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
    
    def __str__(self):
        return f"SMSMessage {self.id} to {self.msisdn} [{self.payload}]"

class SIMLocation(models.Model):
    iccid = models.ForeignKey(SimCard, null=True, blank=True, on_delete=models.SET_NULL, related_name='location')
    sample_time = models.DateTimeField(null=True, blank=True)
    latitude = models.FloatField(default=0, null=True, blank=True)
    longitude = models.FloatField(default=0, null=True, blank=True)

    def __str__(self):
        return f"{self.iccid.label} in {self.latitude}, {self.longitude}"

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

    def __str__(self):
        return f"{self.user} - {self.action} - {self.model_name} ({self.object_id})"
