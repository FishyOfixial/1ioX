from .models import *
from .utils import get_month_range, get_actual_month
from .api_client import get_sim_usage, get_sim_status, get_sim_data_quota, get_sim_sms_quota
from concurrent.futures import ThreadPoolExecutor
from dateutil import parser
from django.db import transaction
from datetime import datetime
import time

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

    all_sims = list(SimCard.objects.all())
    months = get_month_range(6)

    usage_results = []

    def fetch_usage(sim, label, start_dt, end_dt, max_retries=3):
        for attempt in range(1, max_retries + 1):
            try:
                usage = get_sim_usage(sim.iccid, start_dt, end_dt)
                return {
                    'sim': sim,
                    'month': label,
                    'data_volume': usage.total_data_volume,
                    'sms_volume': usage.total_sms_volume
                }
            except Exception as e:
                time.sleep(2)
        print(f"❌ No se pudo obtener status para {sim.iccid} en {label} después de {max_retries} intentos.")
        return None

    print("🟡 Obteniendo datos de uso desde la API...")
    with ThreadPoolExecutor(max_workers=20) as executor:
        args = [
            (sim, label, start_dt, end_dt)
            for sim in all_sims
            for label, start_dt, end_dt in months
        ]
        for result in executor.map(lambda a: fetch_usage(*a), args, chunksize=50):
            if result:
                usage_results.append(result)

    print("🟡 Procesando datos existentes...")
    sim_ids = [u['sim'].id for u in usage_results]
    months_labels = [u['month'] for u in usage_results]
    existing = MonthlySimUsage.objects.filter(sim__id__in=sim_ids, month__in=months_labels)
    existing_map = {(obj.sim.id, obj.month): obj for obj in existing}

    to_create = []
    to_update = []

    print("🟡 Procesando diferencias para guardar...")
    for usage in usage_results:
        key = (usage['sim'].id, usage['month'])
        if key in existing_map:
            obj = existing_map[key]
            if usage['data_volume'] > obj.data_volume or usage['sms_volume'] > obj.sms_volume:
                obj.data_volume = max(obj.data_volume, usage['data_volume'])
                obj.sms_volume = max(obj.sms_volume, usage['sms_volume'])
                to_update.append(obj)
        else:
            to_create.append(MonthlySimUsage(**usage))

    print(f"🟢 Nuevos: {len(to_create)} | Actualizados: {len(to_update)}")

    with transaction.atomic():
        if to_create:
            MonthlySimUsage.objects.bulk_create(to_create, batch_size=500)
        if to_update:
            MonthlySimUsage.objects.bulk_update(to_update, ['data_volume', 'sms_volume'], batch_size=500)

    print("✅ Proceso terminado.")

def save_usage_per_sim_actual_month():
    print("Calculando uso actual por SIM...")

    all_sims = list(SimCard.objects.all())
    month_label, start_dt, end_dt = get_actual_month()

    usage_results = []

    def fetch_usage(sim, max_retries=3):
        for attempt in range(1, max_retries + 1):
            try:
                usage = get_sim_usage(sim.iccid, start_dt, end_dt)
                return {
                    'sim': sim,
                    'month': month_label,
                    'data_volume': usage.total_data_volume,
                    'sms_volume': usage.total_sms_volume
                }
            except Exception as e:
                time.sleep(2)
        print(f"❌ No se pudo obtener status para {sim.iccid} después de {max_retries} intentos.")
        return None

    print("🟡 Obteniendo datos desde la API...")
    with ThreadPoolExecutor(max_workers=30) as executor:
        for result in executor.map(fetch_usage, all_sims, chunksize=50):
            if result:
                usage_results.append(result)

    print("🟡 Procesando datos existentes...")
    sim_ids = [u['sim'].id for u in usage_results]
    existing = MonthlySimUsage.objects.filter(sim__id__in=sim_ids, month=month_label)
    existing_map = {obj.sim: obj for obj in existing}

    to_create = []
    to_update = []

    for usage in usage_results:
        sim = usage['sim']
        if sim in existing_map:
            obj = existing_map[sim]
            if usage['data_volume'] > obj.data_volume or usage['sms_volume'] > obj.sms_volume:
                obj.data_volume = max(obj.data_volume, usage['data_volume'])
                obj.sms_volume = max(obj.sms_volume, usage['sms_volume'])
                to_update.append(obj)
        else:
            to_create.append(MonthlySimUsage(**usage))

    print(f"🟢 Nuevos: {len(to_create)} | Actualizados: {len(to_update)}")

    with transaction.atomic():
        if to_create:
            MonthlySimUsage.objects.bulk_create(to_create, batch_size=500)
        if to_update:
            MonthlySimUsage.objects.bulk_update(to_update, ['data_volume', 'sms_volume'], batch_size=500)

    print("✅ Proceso terminado.")

def save_sim_status():
    print("🟡 Sacando status de las SIMs...")
    all_sims = list(SimCard.objects.all())
    status_results = []

    def fetch_status(sim, max_retries=3):
        for attempt in range(1, max_retries + 1):
            try:
                status = get_sim_status(sim.iccid)
                return {
                    'sim': sim,
                    'status': status.status,
                    'operator_name': status.operator_name,
                    'country_name': status.country_name,
                    'rat_type': status.rat_type,
                    'ue_ip': status.ue_ip,
                    'last_updated': status.last_updated
                }
            except Exception:
                time.sleep(2)
        print(f"❌ No se pudo obtener status para {sim.iccid} después de {max_retries} intentos.")
        return None

    with ThreadPoolExecutor(max_workers=16) as executor:
        for result in executor.map(fetch_status, all_sims, chunksize=50):
            if result:
                status_results.append(result)

    sim_ids = [r['sim'].id for r in status_results]
    existing = SIMStatus.objects.filter(sim_id__in=sim_ids)

    existing_map = {}
    duplicate_ids = []
    for obj in existing:
        if obj.sim_id not in existing_map:
            existing_map[obj.sim_id] = obj
        else:
            duplicate_ids.append(obj.id)

    duplicates_count = len(duplicate_ids)
    if duplicate_ids:
        SIMStatus.objects.filter(id__in=duplicate_ids).delete()

    to_create = []
    to_update = []

    for data in status_results:
        sim_obj = data['sim']
        sim_id = sim_obj.id
        if sim_id in existing_map:
            obj = existing_map[sim_id]
            obj.status = data['status']
            obj.operator_name = data['operator_name']
            obj.country_name = data['country_name']
            obj.rat_type = data['rat_type']
            obj.ue_ip = data['ue_ip']
            obj.last_updated = data['last_updated']
            to_update.append(obj)
        else:
            to_create.append(SIMStatus(
                sim=sim_obj,
                status=data['status'],
                operator_name=data['operator_name'],
                country_name=data['country_name'],
                rat_type=data['rat_type'],
                ue_ip=data['ue_ip'],
                last_updated=data['last_updated']
            ))

    with transaction.atomic():
        if to_create:
            SIMStatus.objects.bulk_create(to_create, batch_size=500)
        if to_update:
            SIMStatus.objects.bulk_update(
                to_update,
                ['status', 'operator_name', 'country_name', 'rat_type', 'ue_ip', 'last_updated'],
                batch_size=500
            )

    print(f"🟢 Proceso terminado. Nuevos: {len(to_create)} | Actualizados: {len(to_update)} | Duplicados eliminados: {duplicates_count}")

def save_sim_quota(quota_type="DATA"):
    print(f"Sacando volumen disponible de {quota_type} en SIMs")

    all_sims = list(SimCard.objects.all())
    quota_results = []

    def fetch_quota(sim, max_retries=3):
        for attempt in range(1, max_retries + 1):
            try:
                if quota_type == "DATA":
                    quota = get_sim_data_quota(sim.iccid)
                else:
                    quota = get_sim_sms_quota(sim.iccid)

                return {
                    'sim': sim,
                    'quota_type': quota_type,
                    'volume': quota.volume,
                    'total_volume': quota.total_volume,
                    'expiry_date': quota.expiry_date,
                    'peak_throughput': quota.peak_throughput,
                    'last_volume_added': quota.last_volume_added,
                    'last_status_change_date': quota.last_status_change_date,
                    'threshold_percentage': quota.threshold_percentage,
                }
            except Exception as e:
                time.sleep(2)
        print(f"❌ No se pudo obtener cuota {quota_type} para {sim.iccid} después de {max_retries} intentos.")
        return None

    with ThreadPoolExecutor(max_workers=8) as executor:
        for result in executor.map(fetch_quota, all_sims, chunksize=50):
            if result:
                quota_results.append(result)

    keys = [(q['sim'].id, q['quota_type']) for q in quota_results]
    existing = SIMQuota.objects.filter(
        sim_id__in=[k[0] for k in keys],
        quota_type=quota_type
    )
    existing_map = {(obj.sim_id, obj.quota_type): obj for obj in existing}

    to_create = []
    to_update = []

    for data in quota_results:
        key = (data['sim'].id, data['quota_type'])
        if key in existing_map:
            obj = existing_map[key]
            if data['volume'] != 0.0:
                obj.volume = data['volume']
                obj.total_volume = data['total_volume']
                obj.expiry_date = data['expiry_date']
                obj.peak_throughput = data['peak_throughput']
                obj.last_volume_added = data['last_volume_added']
                obj.last_status_change_date = data['last_status_change_date']
                obj.threshold_percentage = data['threshold_percentage']
                to_update.append(obj)
        else:
            to_create.append(SIMQuota(**data))

    with transaction.atomic():
        if to_create:
            SIMQuota.objects.bulk_create(to_create, batch_size=500)
        if to_update:
            SIMQuota.objects.bulk_update(
                to_update,
                ['volume', 'total_volume', 'expiry_date', 'peak_throughput',
                'last_volume_added', 'last_status_change_date', 'threshold_percentage'],
                batch_size=500
            )

    print(f"🟢 Proceso terminado ({quota_type}). Nuevos: {len(to_create)} | Actualizados: {len(to_update)}")

def save_sms_log(sms_list, iccid):
    try:
        sim = SimCard.objects.get(iccid=iccid)
    except SimCard.DoesNotExist:
        print(f"No se encontro la SIM con el ICCID {iccid}")
        return

    sms_ids = [sms['id'] for sms in sms_list]
    existing_sms_qs = SMSMessage.objects.filter(id__in=sms_ids)
    existing_sms_map = {sms.id: sms for sms in existing_sms_qs}

    new_objects = []
    update_objects = []

    for sms in sms_list:
        sms_id = sms.get('id')
        if sms_id in existing_sms_map:
            obj = existing_sms_map[sms_id]
            obj.status_id = sms.get('status_id')
            obj.status_description = sms.get('status_description')
            update_objects.append(obj)

        else:
            new_objects.append(SMSMessage(
                id = sms_id,
                sim=sim,
                submit_date=sms.get('submit_date'),
                delivery_date=sms.get('delivery_date'),
                expiry_date=sms.get('expiry_date'),
                retry_count=int(sms.get('retry_count', 0)),
                source_address=sms.get('source_address'),
                msisdn=sms.get('msisdn'),
                udh=sms.get('udh'),
                payload=sms.get('payload'),
                status_id=sms.get('status_id'),
                status_description=sms.get('status_description'),
                sms_type_id=sms.get('sms_type_id'),
                sms_type_description=sms.get('sms_type_description'),
                source_address_type_id=sms.get('source_address_type_id'),
                source_address_type_description=sms.get('source_address_type_description'),
            ))

    if new_objects:
        SMSMessage.objects.bulk_create(new_objects, batch_size=500)

    if update_objects:
        SMSMessage.objects.bulk_update(update_objects, ['status_id', 'status_description'], batch_size=500)

def save_sim_location(location_list, iccid):
    sim = SimCard.objects.get(iccid=iccid)

    if not location_list:
        return
    
    if not isinstance(location_list, list):
        location_list = [location_list]

    def parse_dt(coord):
        return coord.sample_time if coord.sample_time else None
    
    latest_location_data = max(location_list, key=lambda c: parse_dt(c) or datetime.min)
    latest_time = parse_dt(latest_location_data)
    latitude = latest_location_data.latitude
    longitude = latest_location_data.longitude

    sim_location, created = SIMLocation.objects.update_or_create(
        sim=sim,
        defaults={
            'sample_time': latest_time,
            'latitude': latitude,
            'longitude': longitude
        }
    )

