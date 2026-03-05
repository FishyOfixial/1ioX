from django.db import migrations


def migrate_integration_logs(apps, schema_editor):
    try:
        IntegrationLog = apps.get_model("SIM_Control", "IntegrationLog")
    except LookupError:
        return

    SystemLog = apps.get_model("auditlogs", "SystemLog")

    severity_map = {
        "DEBUG": "INFO",
        "INFO": "INFO",
        "WARNING": "WARNING",
        "ERROR": "ERROR",
        "CRITICAL": "CRITICAL",
    }

    batch = []
    for old in IntegrationLog.objects.all().iterator():
        batch.append(
            SystemLog(
                log_type="SYSTEM",
                severity=severity_map.get((old.level or "").upper(), "INFO"),
                message=old.message or "",
                metadata={
                    "deprecated_source": "SIM_Control.IntegrationLog",
                    "logger_name": old.logger_name,
                    "details": old.details or {},
                    "legacy_created_at": old.created_at.isoformat() if old.created_at else None,
                },
                created_at=old.created_at,
            )
        )

    if batch:
        SystemLog.objects.bulk_create(batch, batch_size=500)


class Migration(migrations.Migration):
    dependencies = [
        ("auditlogs", "0001_initial"),
        ("SIM_Control", "0004_rename_sim_control_logger__e4f261_idx_sim_control_logger__31705d_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(migrate_integration_logs, migrations.RunPython.noop),
    ]

