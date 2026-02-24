from datetime import datetime, time

from dateutil.relativedelta import relativedelta
from django.utils import timezone


def normalize_to_midday(dt):
    current_tz = timezone.get_current_timezone()

    if timezone.is_naive(dt):
        aware_dt = timezone.make_aware(dt, current_tz)
    else:
        aware_dt = timezone.localtime(dt, current_tz)

    midday_naive = datetime.combine(aware_dt.date(), time(12, 0, 0))
    return timezone.make_aware(midday_naive, current_tz)


def calculate_new_end_date(start_date, plan):
    base_date = normalize_to_midday(start_date)

    period_unit = plan.period_unit
    period_count = plan.period_count

    if not period_unit or not period_count:
        # Temporary compatibility with legacy plans using duration_days.
        period_unit = "day"
        period_count = plan.duration_days

    if period_unit == "month":
        next_date = base_date + relativedelta(months=period_count)
    elif period_unit == "year":
        next_date = base_date + relativedelta(years=period_count)
    else:
        next_date = base_date + relativedelta(days=period_count)

    return normalize_to_midday(next_date)