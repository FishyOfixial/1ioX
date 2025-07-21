from datetime import datetime
from django.utils.timezone import make_aware, is_naive
from dateutil import parser

class SimCard:
    def __init__(self, data):
        self.iccid = data.get('iccid')
        self.imsi = data.get('imsi')
        self.msisdn = data.get('msisdn')
        self.imei = data.get('imei')
        self.imei_lock = data.get('imei_lock')
        self.status = data.get('status')
        self.activation_date = data.get('activation_date')
        self.ip_address = data.get('ip_address')
        self.current_quota = data.get('current_quota')
        self.quota_status = data.get('quota_status', {}).get('description')
        self.current_quota_SMS = data.get('current_quota_SMS')
        self.quota_status_SMS = data.get('quota_status_SMS', {}).get('description')
        self.label = data.get('label')

class SimUsage:
    def __init__(self, data):
        self.stats = []
        self.total_data_volume = 0
        self.total_sms_volume = 0

        for stat in data.get("stats", []):
            if stat.get("date") == "TOTAL":
                continue

            data_volume = float(stat["data"].get("volume", 0))
            sms_volume = float(stat["sms"].get("volume", 0))

            self.total_data_volume += data_volume
            self.total_sms_volume += sms_volume

            entry = {
                "date": stat.get("date"),
                "data": {
                    "volume": data_volume,
                    "volume_tx": float(stat["data"].get("volume_tx", 0)),
                    "volume_rx": float(stat["data"].get("volume_rx", 0)),
                    "cost": float(stat["data"].get("cost", 0)),
                    "traffic_type": {
                        "description": stat["data"].get("traffic_type", {}).get("description"),
                        "unit": stat["data"].get("traffic_type", {}).get("unit"),
                        "id": stat["data"].get("traffic_type", {}).get("id")
                    },
                    "currency": {
                        "id": stat["data"].get("currency", {}).get("id"),
                        "code": stat["data"].get("currency", {}).get("code"),
                        "symbol": stat["data"].get("currency", {}).get("symbol")
                    }
                },
                "sms": {
                    "volume": sms_volume,
                    "volume_tx": float(stat["sms"].get("volume_tx", 0)),
                    "volume_rx": float(stat["sms"].get("volume_rx", 0)),
                    "cost": float(stat["sms"].get("cost", 0)),
                    "traffic_type": {
                        "description": stat["sms"].get("traffic_type", {}).get("description"),
                        "unit": stat["sms"].get("traffic_type", {}).get("unit"),
                        "id": stat["sms"].get("traffic_type", {}).get("id")
                    },
                    "currency": {
                        "id": stat["sms"].get("currency", {}).get("id"),
                        "code": stat["sms"].get("currency", {}).get("code"),
                        "symbol": stat["sms"].get("currency", {}).get("symbol")
                    }
                }
            }

            self.stats.append(entry)

class ShippingAddress:
    def __init__(self, data):
        self.salutation = data.get("salutation")
        self.first_name = data.get("first_name")
        self.last_name = data.get("last_name")
        self.company = data.get("company")
        self.street = data.get("street")
        self.house_number = data.get("house_number")
        self.address_line2 = data.get("address_line2")
        self.zip = data.get("zip")
        self.city = data.get("city")
        self.country = data.get("country")

class SimInfo:
    def __init__(self, data):
        self.iccid = data.get("iccid")
        self.links = data.get("_links", [])

class Product:
    def __init__(self, data):
        self.product_id = data.get("product_id")
        self.quantity = data.get("quantity")

class Order:
    def __init__(self, data):
        self.order_number = data.get("order_number")
        self.order_type = data.get("order_type")
        self.order_date = data.get("order_date")
        self.order_status = data.get("order_status")
        self.invoice_number = data.get("invoice_number")
        self.invoice_amount = float(data.get("invoice_amount", 0))
        self.currency = data.get("currency")
        self.shipping_address = ShippingAddress(data.get("shipping_address", {}))
        self.sims = [SimInfo(sim) for sim in data.get("sims", [])]
        self.products = [Product(p) for p in data.get("products", [])]

class SimStatus:
    def __init__(self, data):
        location = data.get('location', {})
        operator = location.get('operator', {})
        country = location.get('country', {})
        pdp_context = data.get('pdp_context', {}) or {}
        rat_type = pdp_context.get('rat_type', {}) or {}

        self.iccid = location.get('iccid')
        self.status = data.get('status') or "UNKNOWN"
        self.operator_name = operator.get('name') or ""
        self.country_name = country.get('name') or ""
        self.rat_type = rat_type.get('description') or ""
        self.ue_ip = pdp_context.get('ue_ip_address')

        last_updated_str = location.get('last_updated')
        if last_updated_str:
            dt = datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S")
            self.last_updated = make_aware(dt)
        else:
            self.last_updated = None

class SIMDataQuota:
    def __init__(self, data, iccid):
        self.iccid = iccid
        self.volume = data.get('volume', 0)
        self.total_volume = data.get('total_volume', 0)
        self.expiry_date = self.parse_datetime(data.get('expiry_date'))
        self.peak_throughput = data.get('peak_throughput', 0)
        self.last_volume_added = data.get('last_volume_added', 0)
        self.last_status_change_date = self.parse_datetime(data.get('last_status_change_date'))
        self.threshold_percentage = data.get('threshold_percentage', 0)
        
    def parse_datetime(self, dt_str):
        if dt_str:
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            return make_aware(dt)
        return None
    
class SIMSmsQuota:
    def __init__(self, data, iccid):
        self.iccid = iccid
        self.volume = data.get('volume', 0)
        self.total_volume = data.get('total_volume', 0)
        self.expiry_date = self.parse_datetime(data.get('expiry_date'))
        self.peak_throughput = data.get('peak_throughput', 0)
        self.last_volume_added = data.get('last_volume_added', 0)
        self.last_status_change_date = self.parse_datetime(data.get('last_status_change_date'))
        self.threshold_percentage = data.get('threshold_percentage', 0)
    
    def parse_datetime(self, dt_str):
        if dt_str:
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            return make_aware(dt)
        return None
    
class SMSMessage:
    def __init__(self, data, iccid):
        self.iccid = iccid
        self.id = data.get('id')
        self.submit_date = self.parse_datetime(data.get('submit_date'))
        self.delivery_date = self.parse_datetime(data.get('delivery_date'))
        self.expiry_date = self.parse_datetime(data.get('expiry_date'))
        self.retry_count = int(data.get('retry_count', 0))
        self.source_address = data.get('source_address')
        self.msisdn = data.get('msisdn')
        self.udh = data.get('udh')
        self.payload = data.get('payload')
        status = data.get('status') or {}
        self.status_id = status.get('id')
        self.status_description = status.get('description')
        sms_type = data.get('sms_type') or {}
        self.sms_type_id = sms_type.get('id')
        self.sms_type_description = sms_type.get('description')
        source_address = data.get('source_address_type') or {}
        self.source_address_type_id = source_address.get('id')
        self.source_address_type_description = source_address.get('description')

    def parse_datetime(self, dt_str):
        if dt_str:
            try:
                dt = parser.parse(dt_str)
                return dt
            except Exception:
                return None
        return None