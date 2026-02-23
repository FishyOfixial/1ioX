import threading
from django.core.mail import send_mail
from django.conf import settings
import os
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Cliente

logger = logging.getLogger(__name__)

def send_email_async(subject, message, from_email, recipient_list):
    valid_recipients = [email for email in (recipient_list or []) if email and "@" in email]
    if not valid_recipients:
        logger.warning("Email skipped: no valid recipients for subject='%s'", subject)
        return

    sender = from_email or os.environ.get('SENDER_EMAIL') or settings.DEFAULT_FROM_EMAIL
    if not sender:
        logger.error("Email skipped: no sender configured for subject='%s'", subject)
        return

    try:
        send_mail(subject, message, sender, valid_recipients, fail_silently=False)
    except Exception:
        logger.exception("Email send failed. subject='%s' recipients=%s", subject, valid_recipients)

@receiver(post_save, sender=Cliente)
def send_welcome_email(sender, instance, created, **kwargs):
    if created:
        password = instance.last_name[:2] + instance.first_name[:2] + instance.phone_number[-4:]
        
        threading.Thread(
            target=send_email_async,
            args=(
                '¡Se ha registrado a un nuevo cliente!',
                f"""
                Se ha registrado a {instance.get_full_name()}
                Empresa: {instance.company}
                Ciudad: {instance.city}, {instance.state}
                Teléfono: {instance.phone_number}
                Correo: {instance.email}
                Contraseña: {password}
                """,
                None,
                [os.environ.get('SENDER_EMAIL') or settings.DEFAULT_FROM_EMAIL]
            ),
            daemon=True
        ).start()

        # Correo al cliente
        threading.Thread(
            target=send_email_async,
            args=(
                '¡Haz sido registrado en 1iox!',
                f"""
                Hola, {instance.get_full_name()} haz sido registrado en la plataforma de 1iox.

                Tu información de inicio de sesión
                Usuario: {instance.email}
                Contraseña: {password}
                """,
                None,
                [instance.email]
            ),
            daemon=True
        ).start()
