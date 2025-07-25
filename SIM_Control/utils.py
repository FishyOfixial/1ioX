from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from .models import *
from django.db.models import Sum
from django.core.management import call_command

def is_matriz(user):
    return user.is_authenticated and user.user_type == 'MATRIZ'

def get_last_6_months():
    today = date.today()
    months = []
    for i in range(6):
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
    return (first_day.strftime('%Y-%m'), first_day.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'))

def get_data_monthly_usage(assigned_sims=None):
    qs = MonthlySimUsage.objects.all()
    if assigned_sims is not None:
        qs = qs.filter(iccid__in=assigned_sims)
        
    results = (
        qs.values('month')
        .annotate(
            total_data=Sum('data_volume'),
            total_sms=Sum('sms_volume')
        )
        .order_by('month')
    )
    
    labels = [entry['month'] for entry in results]
    data_volume = [entry['total_data'] for entry in results]
    sms_volume = [entry['total_sms'] for entry in results]

    return labels, data_volume, sms_volume

def get_top_data_usage_per_month(assigned_sims=None):
    UMBRAL_MB = 10
    
    qs = MonthlySimUsage.objects.all()
    if assigned_sims is not None:
        qs = qs.filter(iccid__in=assigned_sims)

    offline_iccids = SimCard.objects.filter(status="Disabled").values_list('iccid', flat=True)
    qs = qs.exclude(iccid__in=offline_iccids)
    months = qs.values_list('month', flat=True).distinct()
    top_sims = []

    for month in months:
        top_sim = (
            qs.filter(month=month, data_volume__gte=UMBRAL_MB)
            .order_by('-data_volume')
        )
        for sim in top_sim:
            top_sims.append({
                'month': month,
                'iccid': sim.iccid,
                'data_used': sim.data_volume
            })

    return top_sims

def get_top_sms_usage_per_month(assigned_sims=None):
    UMBRAL_SMS = 20

    qs = MonthlySimUsage.objects.all()
    if assigned_sims is not None:
        qs = qs.filter(iccid__in=assigned_sims)

    months = qs.values_list('month', flat=True).distinct()
    top_sims = []

    for month in months:
        top_sim = (
            qs.filter(month=month, sms_volume__gte=UMBRAL_SMS)
            .order_by('-sms_volume')
        )
        for sim in top_sim:
            top_sims.append({
                'month': month,
                'iccid': sim.iccid,
                'sms_used': sim.sms_volume
            })

    return top_sims

def get_or_fetch_sms(iccid):
    existing = SMSMessage.objects.filter(iccid=iccid).order_by('-submit_date')
    if existing.exists():
        return existing
    
    try:
        call_command('save_sms', iccid)
    except Exception as e:
        print(f"Error al ejecutar save_sms para {iccid}: {e}")
        return SMSMessage.objects.none()
    
    return SMSMessage.objects.filter(iccid=iccid)

def get_or_fetch_location(iccid):
    try:
        sim = SimCard.objects.get(iccid=iccid)
        call_command('save_location', iccid)
        return SIMLocation.objects.get(iccid=sim)
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

def get_assigned_iccids(user, with_label=False):  
    if user.user_type == 'MATRIZ':
        sims = SimCard.objects.all()
        return sims.values('iccid', 'label') if with_label else sims.values_list('iccid', flat=True)
    model_map = {
        'DISTRIBUIDOR': Distribuidor,
        'REVENDEDOR': Revendedor,
        'FINAL': UsuarioFinal,
    }
    field_map = {
        'DISTRIBUIDOR': 'assigned_to_distribuidor',
        'REVENDEDOR': 'assigned_to_revendedor',
        'FINAL': 'assigned_to_usuario_final',
    }
    model = model_map.get(user.user_type)
    field = field_map.get(user.user_type)
    if not model or not field:
        return []
    related_obj = model.objects.get(user=user)
    filter_kwargs = {field: related_obj}

    qs = SIMAssignation.objects.filter(**filter_kwargs)

    if with_label:
        return qs.values('iccid__iccid', 'iccid__label')
    else:
        return qs.values_list('iccid__iccid', flat=True)

def get_linked_users(user):
    linked_users = []

    if user.user_type == 'DISTRIBUIDOR':
        distribuidor = Distribuidor.objects.get(user=user)

        revendedores = Revendedor.objects.filter(distribuidor=distribuidor).order_by('company')
        for rev in revendedores:
            linked_users.append({
                "user": rev.user,
                "company": rev.company,
                "user_type": "REVENDEDOR"
            })

        clientes = UsuarioFinal.objects.filter(distribuidor=distribuidor).order_by('company')
        for cli in clientes:
            linked_users.append({
                "user": cli.user,
                "company": cli.company,
                "user_type": "CLIENTE"
            })
    elif user.user_type == 'REVENDEDOR':
        revendedor = Revendedor.objects.get(user=user)

        clientes = UsuarioFinal.objects.filter(revendedor=revendedor).order_by('company')
        for cli in clientes:
            linked_users.append({
                "user": cli.user,
                "company": cli.company,
                "user_type": "CLIENTE"
            })
    else:
        distribuidores = Distribuidor.objects.all().order_by('company')
        for dis in distribuidores:
            linked_users.append({
                "user": dis.user,
                "company": dis.company,
                "user_type": "DISTRIBUIDOR"
            })

        revendedores = Revendedor.objects.all().order_by('company')
        for rev in revendedores:
            linked_users.append({
                "user": rev.user,
                "company": rev.company,
                "user_type": "REVENDEDOR"
            })

        clientes = UsuarioFinal.objects.all().order_by('company')
        for cli in clientes:
            linked_users.append({
                "user": cli.user,
                "company": cli.company,
                "user_type": "CLIENTE"
            })
    
    return linked_users
