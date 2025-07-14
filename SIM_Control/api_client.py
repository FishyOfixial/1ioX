import requests, os, asyncio, httpx
from dotenv import load_dotenv
from .sim_class import *
from django.core.management import call_command


load_dotenv()
API_URL = os.environ.get('API_URL')

def get_access_token():
    URL = os.environ.get('AUTH_URL')
    payload = {'grant_type': 'client_credentials'}
    AUTH_HEADER = os.environ.get('API_AUTH_HEADER')
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": AUTH_HEADER
    }
    response = requests.post(URL, json=payload, headers=headers)
    data = response.json()
    return data.get('access_token', '')


def get_all_sims(page=1, page_size=100):
    url = f"{API_URL}sims?page={page}&pageSize={page_size}"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {get_access_token()}"
    }
    response = requests.get(url, headers=headers)
    sims_data = response.json()
    sims = [SimCard(sim) for sim in sims_data]
    total_pages = int(response.headers.get('x-total-pages', 1))
    return sims, total_pages

def get_all_sims_full():
    sims = []
    page = 1
    while True:
        page_sims, total_pages = get_all_sims(page=page)
        sims.extend(page_sims)
        if page >= total_pages:
            break
        page += 1
    sims_dicts = [sim.__dict__ for sim in sims]
    return sims_dicts

def get_sim_usage(iccid, start_dt=None, end_dt=None):
    url = f"{API_URL}sims/{iccid}/usage?start_dt={start_dt}&end_dt={end_dt}"

    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {get_access_token()}"
    }

    response = requests.get(url, headers=headers)
    sims_usage = response.json()
    return SimUsage(sims_usage)

def get_all_orders(page=1, page_size=10):
    url = f"{API_URL}orders?page={page}&pageSize={page_size}&sort=order_number"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {get_access_token()}"
    }
    response = requests.get(url, headers=headers)
    orders_data = response.json()
    orders = [Order(order) for order in orders_data]
    total_pages = int(response.headers.get('x-total-pages', 1))
    return orders, total_pages

def get_all_orders_full():
    orders = []
    page = 1
    while True:
        page_orders, total_pages = get_all_orders(page=page)
        orders.extend(page_orders)
        if page >= total_pages:
            break
        page += 1
    orders_dicts = [order.__dict__ for order in orders]
    return orders_dicts

def get_sim_status(iccid):
    url = f"{API_URL}sims/{iccid}/status"

    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {get_access_token()}"
    }

    response = requests.get(url, headers=headers)
    sim_status = response.json()

    return SimStatus(sim_status)

def get_sim_data_quota(iccid):
    url = f"{API_URL}sims/{iccid}/quota/data"

    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {get_access_token()}"
    }

    response = requests.get(url, headers=headers)
    sim_data_quota = response.json()

    return SIMDataQuota(sim_data_quota, iccid)

def get_sim_sms_quota(iccid):
    url = f"{API_URL}sims/{iccid}/quota/sms"

    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {get_access_token()}"
    }

    response = requests.get(url, headers=headers)
    sim_sms_quota = response.json()

    return SIMSmsQuota(sim_sms_quota, iccid)

def update_sims_status(iccids, labels, status):
    url = f"{API_URL}sims"

    payload = [{"status": status, "label": label, "iccid": iccid} for iccid, label in zip(iccids, labels)]
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {get_access_token()}"
    }
    
    requests.post(url, json=payload, headers=headers)

def update_sim_label(iccid, label, status):
    url = f"{API_URL}sims/{iccid}"
    
    payload = {
        "status": status,
        "label": label,
        "iccid": iccid
    }

    headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": f"Bearer {get_access_token()}"
    }

    requests.put(url, json=payload, headers=headers)
