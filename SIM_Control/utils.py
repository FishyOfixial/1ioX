from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from .models import MonthlySimUsage, SimCard, SMSMessage
from django.db.models import Sum
from django.core.management import call_command

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