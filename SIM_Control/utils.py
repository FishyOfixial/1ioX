from datetime import date, datetime
import logging
from dateutil.relativedelta import relativedelta
from django.core.cache import cache
from django.db.models import Sum
from django.db.models import Q
from django.core.management import call_command
from django.core.exceptions import PermissionDenied

from auditlogs.utils import create_log

from .models import *

logger = logging.getLogger(__name__)

def is_matriz(user):
    return user.is_authenticated and user.user_type == 'MATRIZ'


def log_security_event(message, *, user=None, severity="WARNING", reference_id=None, metadata=None):
    create_log(
        log_type="SYSTEM",
        severity=severity,
        user=user if getattr(user, "is_authenticated", False) else None,
        reference_id=reference_id,
        message=message,
        metadata=metadata,
    )

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
        logger.exception("Error al ejecutar save_sms para %s", sim.iccid)
        return SMSMessage.objects.none()
    
    return SMSMessage.objects.filter(sim=sim)

def get_or_fetch_location(iccid):
    try:
        sim = SimCard.objects.get(iccid=iccid)
        call_command('save_location', iccid)
        return SIMLocation.objects.get(sim=sim)
    except Exception as e:
        logger.exception("Error al ejecutar save_location para %s", iccid)
        return SIMLocation.objects.none()
    
def log_user_action(user, model_name, action, object_id=None, description=None):
    # Deprecated: user action logging disabled in favor of auditlogs.SystemLog.
    return None

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


def get_manageable_users_queryset(user):
    base_qs = User.objects.filter(user_type__in=["DISTRIBUIDOR", "REVENDEDOR", "CLIENTE"])
    if user.user_type == "MATRIZ":
        return base_qs

    if user.user_type == "DISTRIBUIDOR":
        distribuidor = Distribuidor.objects.get(user=user)
        return base_qs.filter(
            Q(user_type="REVENDEDOR", revendedor__distribuidor=distribuidor)
            | Q(user_type="CLIENTE", cliente__distribuidor=distribuidor)
            | Q(user_type="CLIENTE", cliente__revendedor__distribuidor=distribuidor)
        ).distinct()

    if user.user_type == "REVENDEDOR":
        revendedor = Revendedor.objects.get(user=user)
        return base_qs.filter(
            user_type="CLIENTE",
            cliente__revendedor=revendedor,
        ).distinct()

    return User.objects.none()


def get_manageable_user_or_raise(actor, target_user):
    if get_manageable_users_queryset(actor).filter(id=target_user.id).exists():
        return target_user

    log_security_event(
        "Unauthorized user management attempt",
        user=actor,
        metadata={
            "actor_id": actor.id,
            "target_user_id": target_user.id,
            "target_user_type": target_user.user_type,
        },
    )
    raise PermissionDenied("No tienes permiso para administrar este usuario.")


def get_manageable_sim_queryset(user):
    if user.user_type == "MATRIZ":
        return SimCard.objects.all()

    assigned_sims = list(get_assigned_sims(user))
    if not assigned_sims:
        return SimCard.objects.none()
    return SimCard.objects.filter(iccid__in=assigned_sims)


def get_manageable_sims_or_raise(actor, requested_iccids):
    normalized_iccids = []
    seen = set()
    for iccid in requested_iccids:
        iccid_str = str(iccid).strip()
        if not iccid_str or iccid_str in seen:
            continue
        normalized_iccids.append(iccid_str)
        seen.add(iccid_str)

    sims = list(SimCard.objects.filter(iccid__in=normalized_iccids))
    sims_by_iccid = {sim.iccid: sim for sim in sims}
    missing = [iccid for iccid in normalized_iccids if iccid not in sims_by_iccid]
    if missing:
        raise SimCard.DoesNotExist(f"SIMs no encontradas: {', '.join(missing)}")

    authorized_iccids = set(
        get_manageable_sim_queryset(actor)
        .filter(iccid__in=normalized_iccids)
        .values_list("iccid", flat=True)
    )
    unauthorized = [iccid for iccid in normalized_iccids if iccid not in authorized_iccids]
    if unauthorized:
        log_security_event(
            "Unauthorized SIM access attempt",
            user=actor,
            metadata={
                "actor_id": actor.id,
                "iccids": unauthorized,
            },
        )
        raise PermissionDenied("No tienes permiso para administrar una o mas SIMs.")

    return [sims_by_iccid[iccid] for iccid in normalized_iccids]



USER_HIERARCHY = {
    'MATRIZ': ['DISTRIBUIDOR', 'REVENDEDOR', 'CLIENTE'],
    'DISTRIBUIDOR': ['REVENDEDOR', 'CLIENTE'],
    'REVENDEDOR': ['CLIENTE'],
}

SIM_LIST_CACHE_VERSION_PREFIX = "sim-list-version"


def get_sim_list_cache_version(user_id):
    cache_key = f"{SIM_LIST_CACHE_VERSION_PREFIX}:{user_id}"
    version = cache.get(cache_key)
    if version is None:
        cache.set(cache_key, 1, None)
        return 1
    return version


def bump_sim_list_cache_version(user_id):
    cache_key = f"{SIM_LIST_CACHE_VERSION_PREFIX}:{user_id}"
    if cache.get(cache_key) is None:
        cache.set(cache_key, 2, None)
        return 2
    try:
        return cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 2, None)
        return 2


def get_sim_list_affected_user_ids_for_sim_ids(sim_ids):
    normalized_sim_ids = []
    seen = set()
    for sim_id in sim_ids:
        try:
            sim_id_int = int(sim_id)
        except (TypeError, ValueError):
            continue
        if sim_id_int in seen:
            continue
        normalized_sim_ids.append(sim_id_int)
        seen.add(sim_id_int)

    if not normalized_sim_ids:
        return set()

    distribuidor_ct = ContentType.objects.get_for_model(Distribuidor)
    revendedor_ct = ContentType.objects.get_for_model(Revendedor)
    cliente_ct = ContentType.objects.get_for_model(Cliente)

    assignations = list(
        SIMAssignation.objects.filter(sim_id__in=normalized_sim_ids).values("content_type_id", "object_id")
    )

    distribuidor_ids = {row["object_id"] for row in assignations if row["content_type_id"] == distribuidor_ct.id}
    revendedor_ids = {row["object_id"] for row in assignations if row["content_type_id"] == revendedor_ct.id}
    cliente_ids = {row["object_id"] for row in assignations if row["content_type_id"] == cliente_ct.id}

    affected_user_ids = set()

    if distribuidor_ids:
        affected_user_ids.update(
            Distribuidor.objects.filter(id__in=distribuidor_ids).values_list("user_id", flat=True)
        )

    revendedores = list(
        Revendedor.objects.filter(id__in=revendedor_ids).values("user_id", "distribuidor__user_id")
    )
    for revendedor in revendedores:
        if revendedor["user_id"]:
            affected_user_ids.add(revendedor["user_id"])
        if revendedor["distribuidor__user_id"]:
            affected_user_ids.add(revendedor["distribuidor__user_id"])

    clientes = list(
        Cliente.objects.filter(id__in=cliente_ids).values(
            "distribuidor__user_id",
            "revendedor__user_id",
            "revendedor__distribuidor__user_id",
        )
    )
    for cliente in clientes:
        if cliente["distribuidor__user_id"]:
            affected_user_ids.add(cliente["distribuidor__user_id"])
        if cliente["revendedor__user_id"]:
            affected_user_ids.add(cliente["revendedor__user_id"])
        if cliente["revendedor__distribuidor__user_id"]:
            affected_user_ids.add(cliente["revendedor__distribuidor__user_id"])

    return affected_user_ids


def invalidate_sim_list_cache_for_sim_ids(sim_ids):
    affected_user_ids = get_sim_list_affected_user_ids_for_sim_ids(sim_ids)
    for user_id in affected_user_ids:
        bump_sim_list_cache_version(user_id)
    return affected_user_ids

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
