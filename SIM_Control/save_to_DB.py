from .models import *
from .utils import get_last_6_months, get_actual_month
from .api_client import get_sim_usage, get_sim_status, get_sim_data_quota, get_sim_sms_quota
from concurrent.futures import ThreadPoolExecutor
from dateutil import parser
import threading
from collections import defaultdict
from django.db import transaction

db_lock = threading.Lock()

from dateutil import parser

def save_sim_to_db(sim_list):
    iccids = [sim['iccid'] for sim in sim_list if sim.get('iccid')]

    existing_sims = SimCard.objects.in_bulk(iccids, field_name='iccid')

    new_objects = []
    to_update = []

    for sim_data in sim_list:
        iccid = sim_data.get('iccid')
        if not iccid:
            continue

        activation_date = sim_data.get('activation_date')
        try:
            activation_date = parser.parse(activation_date) if activation_date else None
        except Exception:
            activation_date = None

        defaults = {
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

        if iccid in existing_sims:
            obj = existing_sims[iccid]
            for field, value in defaults.items():
                setattr(obj, field, value)
            to_update.append(obj)
        else:
            obj = SimCard(iccid=iccid, **defaults)
            new_objects.append(obj)

    if new_objects:
        SimCard.objects.bulk_create(new_objects, batch_size=500)
    if to_update:
        SimCard.objects.bulk_update(to_update, [
            'imsi', 'msisdn', 'imei', 'imei_lock', 'status', 'activation_date',
            'ip_address', 'current_quota', 'quota_status',
            'current_quota_SMS', 'quota_status_SMS', 'label'
        ], batch_size=500)


def save_order_to_db(order_list):
    shipping_cache = {}
    new_orders = []
    orders_to_update = []
    order_map = {}

    sim_links = []
    product_links = []

    with transaction.atomic():
        existing_orders = Order.objects.in_bulk(
            [o["order_number"] for o in order_list if o.get("order_number")],
            field_name="order_number"
        )

        for order_data in order_list:
            try:
                order_date = parser.parse(order_data.get('order_date')) if order_data.get('order_date') else None
            except Exception:
                order_date = None

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

            shipping_key = (shipping_data.get("street"), shipping_data.get("zip"))
            if shipping_key not in shipping_cache:
                shipping_obj, _ = ShippingAddress.objects.update_or_create(
                    street=shipping_data.get("street"),
                    zip=shipping_data.get("zip"),
                    defaults=shipping_data
                )
                shipping_cache[shipping_key] = shipping_obj
            else:
                shipping_obj = shipping_cache[shipping_key]

            order_number = order_data.get("order_number")
            order_defaults = {
                "order_type": order_data.get("order_type"),
                "order_date": order_date,
                "order_status": order_data.get("order_status"),
                "invoice_number": order_data.get("invoice_number"),
                "invoice_amount": order_data.get("invoice_amount"),
                "currency": order_data.get("currency"),
                "shipping_address": shipping_obj,
            }

            if order_number in existing_orders:
                order_obj = existing_orders[order_number]
                for field, value in order_defaults.items():
                    setattr(order_obj, field, value)
                orders_to_update.append(order_obj)
            else:
                order_obj = Order(order_number=order_number, **order_defaults)
                new_orders.append(order_obj)

            order_map[order_number] = order_obj

        if new_orders:
            Order.objects.bulk_create(new_orders, batch_size=500)
        if orders_to_update:
            Order.objects.bulk_update(orders_to_update, [
                "order_type", "order_date", "order_status", "invoice_number",
                "invoice_amount", "currency", "shipping_address"
            ], batch_size=500)

        all_orders = {o.order_number: o for o in Order.objects.filter(order_number__in=order_map)}

        OrderSIM.objects.filter(order__order_number__in=order_map).delete()
        OrderProduct.objects.filter(order__order_number__in=order_map).delete()

        for order_data in order_list:
            order_number = order_data.get("order_number")
            order_obj = all_orders[order_number]

            for sim in order_data.get("sims", []):
                sim_links.append(OrderSIM(order=order_obj, iccid=sim.iccid))

            for product in order_data.get("products", []):
                product_links.append(OrderProduct(
                    order=order_obj,
                    product_id=product.product_id,
                    quantity=product.quantity
                ))

        if sim_links:
            OrderSIM.objects.bulk_create(sim_links, batch_size=500)
        if product_links:
            OrderProduct.objects.bulk_create(product_links, batch_size=500)


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

    with ThreadPoolExecutor(max_workers=30) as executor:
        executor.map(process_sim, all_sims)

    print(f"✅ Proceso terminado.")

def save_usage_per_sim_actual_month():
    print("Calculando uso actual por SIM...")

    all_sims = SimCard.objects.values_list('iccid', flat=True)
    month = get_actual_month()

    def process_sim(iccid):
        try:
            usage = get_sim_usage(iccid, month[1], month[2])
            with db_lock:
                obj, created = MonthlySimUsage.objects.get_or_create(
                    iccid=iccid,
                    month=month[0],
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
            print(f"Error con {iccid} en {month[0]}: {e}")

    with ThreadPoolExecutor(max_workers=30) as executor:
        executor.map(process_sim, all_sims)

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

    with ThreadPoolExecutor(max_workers=10) as executor:
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

    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(process_sim, all_sims)

    print(f"✅ Proceso terminado.")