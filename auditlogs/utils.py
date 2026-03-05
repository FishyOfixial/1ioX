def create_log(
    log_type,
    message,
    severity="INFO",
    user=None,
    reference_id=None,
    metadata=None,
):
    from .models import SystemLog

    SystemLog.objects.create(
        log_type=log_type,
        severity=severity,
        user=user,
        reference_id=reference_id,
        message=message,
        metadata=metadata,
    )

