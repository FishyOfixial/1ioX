from .models import *
from .utils import get_last_6_months
from .api_client import get_sim_usage, get_sim_status, get_sim_data_quota, get_sim_sms_quota
from concurrent.futures import ThreadPoolExecutor
from dateutil import parser
import threading

db_lock = threading.Lock()

def save_sim_to_db(sim_list):
    for sim_data in sim_list:
        activation_date = sim_data.get('activation_date')
        if activation_date:
            try:
                activation_date = parser.parse(activation_date)
            except Exception:
                activation_date = None
        else:
            activation_date = None

        SimCard.objects.update_or_create(
            iccid=sim_data.get('iccid'),
            defaults={
                'imsi': sim_data.get('imsi'),
                'msisdn': sim_data.get('msisdn'),
                'imei': sim_data.get('imei'),
                'imei_lock': sim_data.get('imei_lock') or False,
                'status': sim_data.get('status'),
                'activation_date': activation_date,
                'ip_address': sim_data.get('ip_address'),
                'current_quota': sim_data.get('current_quota'),
                'quota_status': sim_data.get('quota_status'),
                'current_quota_SMS': sim_data.get('current_quota_SMS'),
                'quota_status_SMS': sim_data.get('quota_status_SMS'),
                'label': sim_data.get('label'),
            }
        )

def save_order_to_db(order_list):
    for order_data in order_list:
        try:
            order_date = parser.parse(order_data.get('order_date')) if order_data.get('order_date') else None
        except Exception:
            order_date = None

        # Guardar dirección de envío
        shipping_data = order_data.get('shipping_address', {})

        if not isinstance(shipping_data, dict):
            shipping_data = {
                "salutation": getattr(shipping_data, "salutation", None),
                "first_name": getattr(shipping_data, "first_name", None),
                "last_name": getattr(shipping_data, "last_name", None),
                "company": getattr(shipping_data, "company", None),
                "street": getattr(shipping_data, "street", None),
                "house_number": getattr(shipping_data, "house_number", None),
                "address_line2": getattr(shipping_data, "address_line2", None),
                "zip": getattr(shipping_data, "zip", None),
                "city": getattr(shipping_data, "city", None),
                "country": getattr(shipping_data, "country", None),
            }

        shipping_obj, _ = ShippingAddress.objects.update_or_create(
            street=shipping_data.get("street"),
            zip=shipping_data.get("zip"),
            defaults={
                "salutation": shipping_data.get("salutation"),
                "first_name": shipping_data.get("first_name"),
                "last_name": shipping_data.get("last_name"),
                "company": shipping_data.get("company"),
                "house_number": shipping_data.get("house_number"),
                "address_line2": shipping_data.get("address_line2"),
                "city": shipping_data.get("city"),
                "country": shipping_data.get("country"),
            }
        )


        # Guardar la orden
        order_obj, _ = Order.objects.update_or_create(
            order_number=order_data.get("order_number"),
            defaults={
                "order_type": order_data.get("order_type"),
                "order_date": order_date,
                "order_status": order_data.get("order_status"),
                "invoice_number": order_data.get("invoice_number"),
                "invoice_amount": order_data.get("invoice_amount"),
                "currency": order_data.get("currency"),
                "shipping_address": shipping_obj,
            }
        )

        # Guardar SIMs asociadas
        OrderSIM.objects.filter(order=order_obj).delete()
        for sim in order_data.get("sims", []):
            OrderSIM.objects.create(
                order=order_obj,
                iccid=sim.iccid
            )

        # Guardar productos asociados
        OrderProduct.objects.filter(order=order_obj).delete()
        for product in order_data.get("products", []):
            OrderProduct.objects.create(
                order=order_obj,
                product_id=product.product_id,
                quantity=product.quantity,
            )

def save_usage_per_sim_month():
    print("Calculando uso mensual por SIM...")

    all_sims = SimCard.objects.values_list('iccid', flat=True)
    months = get_last_6_months()

    def process_sim(iccid):
        for label, start_dt, end_dt in months:
            try:
                usage = get_sim_usage(iccid, start_dt, end_dt)
                with db_lock:
                    obj, created = MonthlySimUsage.objects.get_or_create(
                        iccid=iccid,
                        month=label,
                        defaults={
                            'data_volume': usage.total_data_volume,
                            'sms_volume': usage.total_sms_volume
                        }
                    )
                    if not created:
                        if (
                            usage.total_data_volume > obj.data_volume or
                            usage.total_sms_volume > obj.sms_volume
                        ):
                            obj.data_volume = max(obj.data_volume, usage.total_data_volume)
                            obj.sms_volume = max(obj.sms_volume, usage.total_sms_volume)
                            obj.save()
            except Exception as e:
                print(f"Error con {iccid} en {label}: {e}")

    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(process_sim, all_sims)

    print(f"✅ Proceso terminado.")

def save_sim_status():
    print("Sacando status de las SIMs...")
    all_sims = SimCard.objects.values_list('iccid', flat=True)
    
    def process_sim(iccid):
        try:
            status = get_sim_status(iccid)
            with db_lock:
                obj, created = SIMStatus.objects.update_or_create(
                    iccid = iccid,
                    defaults= {
                        'status': status.status,
                        'operator_name': status.operator_name,
                        'country_name': status.country_name,
                        'rat_type': status.rat_type,
                        'ue_ip': status.ue_ip,
                        'last_updated': status.last_updated
                    }
                )
        except Exception as e:
                print(f"Error con {iccid}: {e}")

    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(process_sim, all_sims)

    print(f"✅ Proceso terminado.")

def save_sim_data_quota():
    print("Sacando volumen disponible de datos en SIMs")
    all_sims = SimCard.objects.values_list('iccid', flat=True)

    def process_sim(iccid):
        try:
            status = get_sim_data_quota(iccid)
            with db_lock:
                obj, created = SIMQuota.objects.get_or_create(
                    iccid = iccid,
                    defaults = {
                        'volume': status.volume,
                        'total_volume': status.total_volume,
                        'expiry_date': status.expiry_date,
                        'peak_throughput': status.peak_throughput,
                        'last_volume_added': status.last_volume_added,
                        'last_status_change_date': status.last_status_change_date,
                        'threshold_percentage': status.threshold_percentage
                    }
                )
                if not created:
                    if status.volume != 0.0:
                        obj.volume = status.volume
                        obj.save()
        except Exception as e:
                print(f"Error con {iccid}: {e}")

    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(process_sim, all_sims)

    print(f"✅ Proceso terminado.")

def save_sim_sms_quota():
    print("Sacando volumen disponible de SMS en SIMs")
    all_sims = SimCard.objects.values_list('iccid', flat=True)

    def process_sim(iccid):
        try:
            quota = get_sim_sms_quota(iccid)
            with db_lock:
                obj, created = SIMSMSQuota.objects.get_or_create(
                    iccid = iccid,
                    defaults = {
                        'volume': quota.volume,
                        'total_volume': quota.total_volume,
                        'expiry_date': quota.expiry_date,
                        'peak_throughput': quota.peak_throughput,
                        'last_volume_added': quota.last_volume_added,
                        'last_status_change_date': quota.last_status_change_date,
                        'threshold_percentage': quota.threshold_percentage
                    }
                )
                if not created:
                    if quota.volume != 0.0:
                        obj.volume = quota.volume
                        obj.save()
        except Exception as e:
                print(f"Error con {iccid}: {e}")

    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(process_sim, all_sims)

    print(f"✅ Proceso terminado.")