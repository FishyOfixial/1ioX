from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from django.db.models import Sum
from django.db.models import Q
from django.core.management import call_command
from django.utils import timezone
from .models import *

def is_matriz(user):
    return user.is_authenticated and user.user_type == 'MATRIZ'

def get_month_range(n_months=6):
    today = date.today()
    months = []
    for i in range(n_months):
        month_start = (today - relativedelta(months=i)).replace(day=1)
        next_month = month_start + relativedelta(months=1)
        months.append((
            month_start.strftime('%Y-%m'),
            month_start.strftime('%Y-%m-%d'),
            (next_month - relativedelta(days=1)).strftime('%Y-%m-%d')
        ))
    return months[::-1]

def get_actual_month():
    today = datetime.now().date()
    first_day = date(today.year, today.month, 1)
    return first_day.strftime('%Y-%m'), first_day.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')

def get_data_monthly_usage(assigned_sims=None):
    qs = MonthlySimUsage.objects.all()
    if assigned_sims is not None:
        qs = qs.filter(sim__id__in=assigned_sims)
        
    results = (
        qs.values('month')
        .annotate(
            total_data=Sum('data_volume'),
            total_sms=Sum('sms_volume')
        )
        .order_by('-month')[:6]
    )
    results = sorted(results, key=lambda x: x['month'])

    labels = [entry['month'] for entry in results]
    data_volume = [entry['total_data'] for entry in results]
    sms_volume = [entry['total_sms'] for entry in results]

    return labels, data_volume, sms_volume

def get_top_usage_per_month(field, threshold, assigned_sims=None):
    qs = MonthlySimUsage.objects.all()

    if assigned_sims:
        qs = qs.filter(sim__id__in=assigned_sims)

    qs = qs.exclude(sim__status="Disabled").filter(**{f"{field}__gte": threshold}).select_related('sim').order_by('month', f"-{field}")

    top_sims = []
    for sim_usage in qs:
        value = getattr(sim_usage, field) or 0
        top_sims.append({
            'month': sim_usage.month,
            'iccid': sim_usage.sim.iccid,
            f"{field}_used": value
        })
    return top_sims

def get_top_data_usage_per_month(assigned_sims=None):
    return get_top_usage_per_month('data_volume', 10, assigned_sims)

def get_top_sms_usage_per_month(assigned_sims=None):
    return get_top_usage_per_month('sms_volume', 20, assigned_sims)

def get_or_fetch_sms(sim):
    existing = SMSMessage.objects.filter(sim=sim).order_by('-submit_date')
    if existing.exists():
        return existing
    
    try:
        call_command('save_sms', sim.iccid)
    except Exception as e:
        print(f"Error al ejecutar save_sms para {sim.iccid}: {e}")
        return SMSMessage.objects.none()
    
    return SMSMessage.objects.filter(sim=sim)

def get_or_fetch_location(iccid):
    try:
        sim = SimCard.objects.get(iccid=iccid)
        call_command('save_location', iccid)
        return SIMLocation.objects.get(sim=sim)
    except Exception as e:
        print(f"Error al ejecutar save_location para {iccid}: {e}")
        return SIMLocation.objects.none()
    
def log_user_action(user, model_name, action, object_id=None, description=None):
    UserActionLog.objects.create(
        user=user,
        object_id = object_id if object_id else None,
        model_name= model_name,
        action=action,
        description=description,
        timestamp = timezone.now(),
    )

MODEL_MAP = {
    'DISTRIBUIDOR': Distribuidor,
    'REVENDEDOR': Revendedor,
    'CLIENTE': Cliente,
}

def get_assigned_sims(user, with_label=False):
    if user.user_type == 'MATRIZ':
        sims = SimCard.objects.all()
        return sims.values('iccid', 'label') if with_label else sims.values_list('iccid', flat=True)

    model = MODEL_MAP.get(user.user_type)
    if not model:
        return []

    related_obj = model.objects.get(user=user)

    query_objects = [related_obj]

    if user.user_type == 'DISTRIBUIDOR':
        query_objects.extend(related_obj.revendedores.all())
        query_objects.extend(related_obj.clientes.all())
    elif user.user_type == 'REVENDEDOR':
        query_objects.extend(related_obj.clientes.all())

    targets_by_ct = {}
    for obj in query_objects:
        ct_id = ContentType.objects.get_for_model(obj.__class__).id
        targets_by_ct.setdefault(ct_id, []).append(obj.id)

    query = Q()
    for ct_id, object_ids in targets_by_ct.items():
        query |= Q(content_type_id=ct_id, object_id__in=object_ids)

    sims_set = set()
    if query:
        qs = SIMAssignation.objects.filter(query).select_related('sim')
        for assign in qs:
            if assign.sim:
                sims_set.add((assign.sim.iccid, assign.sim.label) if with_label else assign.sim.iccid)

    return list(sims_set)



USER_HIERARCHY = {
    'MATRIZ': ['DISTRIBUIDOR', 'REVENDEDOR', 'CLIENTE'],
    'DISTRIBUIDOR': ['REVENDEDOR', 'CLIENTE'],
    'REVENDEDOR': ['CLIENTE'],
}

def get_linked_users(user):
    linked_users = []
    distribuidor_obj = None
    revendedor_obj = None
    if user.user_type == 'DISTRIBUIDOR':
        distribuidor_obj = Distribuidor.objects.get(user=user)
    elif user.user_type == 'REVENDEDOR':
        revendedor_obj = Revendedor.objects.get(user=user)

    for user_type in USER_HIERARCHY.get(user.user_type, []):
        model = MODEL_MAP[user_type]
        if user.user_type != 'MATRIZ':
            filter_kwargs = {}
            if user.user_type == 'DISTRIBUIDOR' and user_type == 'REVENDEDOR':
                filter_kwargs['distribuidor'] = distribuidor_obj
            elif user.user_type == 'DISTRIBUIDOR' and user_type == 'CLIENTE':
                filter_kwargs['distribuidor'] = distribuidor_obj
            elif user.user_type == 'REVENDEDOR':
                filter_kwargs['revendedor'] = revendedor_obj
            queryset = model.objects.filter(**filter_kwargs).order_by('company')
        else:
            queryset = model.objects.all().order_by('company')

        for obj in queryset:
            linked_users.append({
                'user': obj.user,
                'company': obj.company,
                'user_type': user_type
            })
    return linked_users

def get_limits():
    limits, _ = GlobalLimits.objects.get_or_create(pk=1)
    return limits.data_limit, limits.mt_limit, limits.mo_limit
