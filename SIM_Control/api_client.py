import requests, os, json
from dotenv import load_dotenv
from .sim_class import *
import time
from concurrent.futures import ThreadPoolExecutor

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()
API_URL = os.environ.get('API_URL')
AUTH_URL = os.environ.get('AUTH_URL')
API_AUTH_HEADER = os.environ.get('API_AUTH_HEADER')
API_TIMEOUT = int(os.environ.get('API_TIMEOUT', 30))
session = requests.Session()

retry_strategy = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=("GET", "POST", "PUT"),
    raise_on_status=False,
)
adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=50, pool_maxsize=50)
session.mount("https://", adapter)
session.mount("http://", adapter)

_token_cache = {
    'token': None,
    'expires_at': 0
}

def get_access_token():
    if _token_cache['token'] and time.time() < _token_cache['expires_at']:
        return _token_cache['token']

    payload = {'grant_type': 'client_credentials'}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": API_AUTH_HEADER
    }
    response = session.post(AUTH_URL, json=payload, headers=headers, timeout=API_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    token = data.get('access_token', '')
    expires_in = data.get('expires_in', 3600)
    _token_cache['token'] = token
    _token_cache['expires_at'] = time.time() + expires_in - 60
    return token

def get_auth_headers(content_type_json=False):
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {get_access_token()}"
    }
    if content_type_json:
        headers["content-type"] = "application/json"
    return headers

def get_all_sims(page=1, page_size=100):
    url = f"{API_URL}sims?page={page}&pageSize={page_size}"
    headers = get_auth_headers()
    response = session.get(url, headers=headers, timeout=API_TIMEOUT)
    response.raise_for_status()
    sims_data = response.json()
    sims = [SimCard(sim) for sim in sims_data]
    total_pages = int(response.headers.get('x-total-pages', 1))
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

    sims_dicts = [sim.__dict__ for sim in sims]
    return sims_dicts

def get_sim_usage(iccid, start_dt=None, end_dt=None):
    url = f"{API_URL}sims/{iccid}/usage?start_dt={start_dt}&end_dt={end_dt}"
    headers = get_auth_headers()
    response = session.get(url, headers=headers, timeout=API_TIMEOUT)
    response.raise_for_status()
    sims_usage = response.json()
    return SimUsage(sims_usage)

def get_all_orders(page=1, page_size=10):
    url = f"{API_URL}orders?page={page}&pageSize={page_size}&sort=order_number"
    headers = get_auth_headers()
    response = session.get(url, headers=headers, timeout=API_TIMEOUT)
    response.raise_for_status()
    orders_data = response.json()
    orders = [Order(order) for order in orders_data]
    total_pages = int(response.headers.get('x-total-pages', 1))
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

    orders_dicts = [order.__dict__ for order in orders]
    return orders_dicts

def get_sim_status(iccid):
    url = f"{API_URL}sims/{iccid}/status"
    headers = get_auth_headers()
    response = session.get(url, headers=headers, timeout=API_TIMEOUT)
    response.raise_for_status()
    sim_status = response.json()
    return SimStatus(sim_status)

def get_sim_data_quota(iccid):
    url = f"{API_URL}sims/{iccid}/quota/data"
    headers = get_auth_headers()
    response = session.get(url, headers=headers, timeout=API_TIMEOUT)
    response.raise_for_status()
    sim_data_quota = response.json()
    return SIMDataQuota(sim_data_quota, iccid)

def get_sim_sms_quota(iccid):
    url = f"{API_URL}sims/{iccid}/quota/sms"
    headers = get_auth_headers()
    response = session.get(url, headers=headers, timeout=API_TIMEOUT)
    response.raise_for_status()
    sim_sms_quota = response.json()
    return SIMSmsQuota(sim_sms_quota, iccid)

def update_sims_status(iccids, labels, status):
    url = f"{API_URL}sims"
    payload = [{"status": status, "label": label, "iccid": iccid} for iccid, label in zip(iccids, labels)]
    headers = get_auth_headers(content_type_json=True)
    response = session.post(url, json=payload, headers=headers, timeout=API_TIMEOUT)
    response.raise_for_status()

def update_sim_label(iccid, label, status):
    url = f"{API_URL}sims/{iccid}"
    payload = { "status": status, "label": label, "iccid": iccid}
    headers = get_auth_headers(content_type_json=True)
    response = session.put(url, json=payload, headers=headers, timeout=API_TIMEOUT)
    response.raise_for_status()

def get_sim_sms(iccid, page=1, page_size=100):
    url = f"{API_URL}sims/{iccid}/sms?page={page}&pageSize={page_size}"
    headers = get_auth_headers()
    response = session.get(url, headers=headers, timeout=API_TIMEOUT)
    response.raise_for_status()
    sms_page = response.json()
    sms = [SMSMessage(message, iccid) for message in sms_page]
    total_pages = int(response.headers.get('x-total-pages', 1))
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
    sms_dicts = [sm.__dict__ for sm in sms]
    return sms_dicts

def send_sms_api(iccid, source_address, command):
    url = f"{API_URL}sims/{iccid}/sms"
    payload_dict = {
        "source_address": source_address,
        "payload": command,
    }
    payload = json.dumps(payload_dict)
    headers = get_auth_headers(content_type_json=True)
    response = session.post(url, data=payload, headers=headers, timeout=API_TIMEOUT)
    response.raise_for_status()

def get_sim_location_api(iccid):
    url = f"{API_URL}locate/devices/{iccid}/positions?page=1&pageSize=100&mode=ALL"
    headers = get_auth_headers()
    response = session.get(url, headers=headers, timeout=API_TIMEOUT)
    response.raise_for_status()
    sim_location = response.json()
    return SIMLocation(sim_location, iccid)

def create_global_limits(data, mt, mo):
    url = f"{API_URL}sims/limits"
    headers = get_auth_headers(content_type_json=True)
    payload = { 'dataLimitId': data, 'smsMtLimitId': mt, 'smsMoLimitId': mo }
    response = session.post(url, json=payload, headers=headers, timeout=API_TIMEOUT)
    response.raise_for_status()
    
