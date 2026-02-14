from django.db import migrations, models
from django.db.models import Count, Min


def dedupe_monthly_usage(apps, schema_editor):
    MonthlySimUsage = apps.get_model('SIM_Control', 'MonthlySimUsage')
    duplicated = (
        MonthlySimUsage.objects.values('sim_id', 'month')
        .annotate(total=Count('id'), keep_id=Min('id'))
        .filter(total__gt=1)
    )
    for row in duplicated.iterator():
        MonthlySimUsage.objects.filter(
            sim_id=row['sim_id'],
            month=row['month'],
        ).exclude(id=row['keep_id']).delete()


def dedupe_sim_assignation(apps, schema_editor):
    SIMAssignation = apps.get_model('SIM_Control', 'SIMAssignation')
    duplicated = (
        SIMAssignation.objects.values('sim_id', 'content_type_id', 'object_id')
        .annotate(total=Count('id'), keep_id=Min('id'))
        .filter(total__gt=1)
    )
    for row in duplicated.iterator():
        SIMAssignation.objects.filter(
            sim_id=row['sim_id'],
            content_type_id=row['content_type_id'],
            object_id=row['object_id'],
        ).exclude(id=row['keep_id']).delete()


def dedupe_sim_status(apps, schema_editor):
    SIMStatus = apps.get_model('SIM_Control', 'SIMStatus')
    duplicated = (
        SIMStatus.objects.values('sim_id')
        .annotate(total=Count('id'), keep_id=Min('id'))
        .filter(total__gt=1)
    )
    for row in duplicated.iterator():
        SIMStatus.objects.filter(sim_id=row['sim_id']).exclude(id=row['keep_id']).delete()


def dedupe_sim_quota(apps, schema_editor):
    SIMQuota = apps.get_model('SIM_Control', 'SIMQuota')
    duplicated = (
        SIMQuota.objects.values('sim_id', 'quota_type')
        .annotate(total=Count('id'), keep_id=Min('id'))
        .filter(total__gt=1)
    )
    for row in duplicated.iterator():
        SIMQuota.objects.filter(
            sim_id=row['sim_id'],
            quota_type=row['quota_type'],
        ).exclude(id=row['keep_id']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('SIM_Control', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(dedupe_monthly_usage, migrations.RunPython.noop),
        migrations.RunPython(dedupe_sim_assignation, migrations.RunPython.noop),
        migrations.RunPython(dedupe_sim_status, migrations.RunPython.noop),
        migrations.RunPython(dedupe_sim_quota, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='monthlysimusage',
            constraint=models.UniqueConstraint(fields=('sim', 'month'), name='uq_monthly_usage_sim_month'),
        ),
        migrations.AddConstraint(
            model_name='simassignation',
            constraint=models.UniqueConstraint(fields=('sim', 'content_type', 'object_id'), name='uq_sim_assignation_target'),
        ),
        migrations.AddConstraint(
            model_name='simstatus',
            constraint=models.UniqueConstraint(fields=('sim',), name='uq_sim_status_sim'),
        ),
        migrations.AddConstraint(
            model_name='simquota',
            constraint=models.UniqueConstraint(fields=('sim', 'quota_type'), name='uq_sim_quota_sim_type'),
        ),
    ]
