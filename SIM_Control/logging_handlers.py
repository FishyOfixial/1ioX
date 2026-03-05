import logging
import traceback

from auditlogs.utils import create_log


class IntegrationDBLogHandler(logging.Handler):
    allowed_loggers = {"billing.mercadopago", "billing.1nce"}

    def emit(self, record):
        if record.name not in self.allowed_loggers:
            return

        try:
            message = record.getMessage()
            metadata = {"logger_name": record.name}
            if record.exc_info:
                metadata["exception"] = "".join(traceback.format_exception(*record.exc_info))
            create_log(
                log_type="SYSTEM",
                severity=record.levelname if record.levelname in {"INFO", "WARNING", "ERROR", "CRITICAL"} else "INFO",
                message=message[:4000],
                metadata=metadata,
            )
        except Exception:
            # Never crash request/command flow due to logger persistence.
            return
