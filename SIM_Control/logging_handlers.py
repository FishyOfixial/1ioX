import logging
import traceback

from django.apps import apps


class IntegrationDBLogHandler(logging.Handler):
    allowed_loggers = {"billing.1nce", "billing.mercadopago"}

    def emit(self, record):
        if record.name not in self.allowed_loggers:
            return

        try:
            IntegrationLog = apps.get_model("SIM_Control", "IntegrationLog")
            message = record.getMessage()
            details = {}
            if record.exc_info:
                details["exception"] = "".join(traceback.format_exception(*record.exc_info))

            IntegrationLog.objects.create(
                logger_name=record.name,
                level=record.levelname,
                message=message[:4000],
                details=details,
            )
        except Exception:
            # Never crash request/command flow due to logger persistence.
            return
