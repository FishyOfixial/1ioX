from concurrent.futures import ThreadPoolExecutor

import requests

from billing.services.one_nce_client import OneNCEClient
from .sim_class import Order, SIMDataQuota, SIMLocation, SIMSmsQuota, SMSMessage, SimCard, SimStatus, SimUsage

_client = OneNCEClient()


def _request_or_raise(method, endpoint, *, json_payload=None):
    response = _client._request(method, endpoint, json_payload=json_payload)
    if response is None:
        raise requests.RequestException(f"1NCE request failed for {method.upper()} {endpoint}")
    response.raise_for_status()
    return response


def get_all_sims(page=1, page_size=100):
    endpoint = f"sims?page={page}&pageSize={page_size}"
    response = _request_or_raise("get", endpoint)
    sims_data = response.json()
    sims = [SimCard(sim) for sim in sims_data]
    total_pages = int(response.headers.get("x-total-pages", 1))
    return sims, total_pages


def get_all_sims_full():
    first_page_sims, total_pages = get_all_sims(page=1)
    sims = list(first_page_sims)

    if total_pages > 1:
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(get_all_sims, page) for page in range(2, total_pages + 1)]
            for future in futures:
                page_sims, _ = future.result()
                sims.extend(page_sims)

    return [sim.__dict__ for sim in sims]


def get_sim_usage(iccid, start_dt=None, end_dt=None):
    endpoint = f"sims/{iccid}/usage?start_dt={start_dt}&end_dt={end_dt}"
    response = _request_or_raise("get", endpoint)
    return SimUsage(response.json())


def get_all_orders(page=1, page_size=10):
    endpoint = f"orders?page={page}&pageSize={page_size}&sort=order_number"
    response = _request_or_raise("get", endpoint)
    orders_data = response.json()
    orders = [Order(order) for order in orders_data]
    total_pages = int(response.headers.get("x-total-pages", 1))
    return orders, total_pages


def get_all_orders_full():
    first_page_orders, total_pages = get_all_orders(page=1)
    orders = list(first_page_orders)

    if total_pages > 1:
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(get_all_orders, page) for page in range(2, total_pages + 1)]
            for future in futures:
                page_orders, _ = future.result()
                orders.extend(page_orders)

    return [order.__dict__ for order in orders]


def get_sim_status(iccid):
    endpoint = f"sims/{iccid}/status"
    response = _request_or_raise("get", endpoint)
    return SimStatus(response.json())


def get_sim_data_quota(iccid):
    endpoint = f"sims/{iccid}/quota/data"
    response = _request_or_raise("get", endpoint)
    return SIMDataQuota(response.json(), iccid)


def get_sim_sms_quota(iccid):
    endpoint = f"sims/{iccid}/quota/sms"
    response = _request_or_raise("get", endpoint)
    return SIMSmsQuota(response.json(), iccid)


def update_sims_status(iccids, labels, status):
    endpoint = "sims"
    payload = [{"status": status, "label": label, "iccid": iccid} for iccid, label in zip(iccids, labels)]
    _request_or_raise("post", endpoint, json_payload=payload)


def update_sim_label(iccid, label, status):
    endpoint = f"sims/{iccid}"
    payload = {"status": status, "label": label, "iccid": iccid}
    _request_or_raise("put", endpoint, json_payload=payload)


def get_sim_sms(iccid, page=1, page_size=100):
    endpoint = f"sims/{iccid}/sms?page={page}&pageSize={page_size}"
    response = _request_or_raise("get", endpoint)
    sms_page = response.json()
    sms = [SMSMessage(message, iccid) for message in sms_page]
    total_pages = int(response.headers.get("x-total-pages", 1))
    return sms, total_pages


def get_sim_sms_all(iccid):
    sms = []
    page = 1
    while True:
        page_sms, total_pages = get_sim_sms(iccid, page=page)
        sms.extend(page_sms)
        if page >= total_pages:
            break
        page += 1
    return [sm.__dict__ for sm in sms]


def send_sms_api(iccid, source_address, command):
    endpoint = f"sims/{iccid}/sms"
    payload_dict = {
        "source_address": source_address,
        "payload": command,
    }
    response = _request_or_raise("post", endpoint, json_payload=payload_dict)
    return response


def get_sim_location_api(iccid):
    endpoint = f"locate/devices/{iccid}/positions?page=1&pageSize=100&mode=ALL"
    response = _request_or_raise("get", endpoint)
    return SIMLocation(response.json(), iccid)


def create_global_limits(data, mt, mo):
    endpoint = "sims/limits"
    payload = {"dataLimitId": data, "smsMtLimitId": mt, "smsMoLimitId": mo}
    _request_or_raise("post", endpoint, json_payload=payload)
