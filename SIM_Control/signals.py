import threading
from django.core.mail import send_mail
import os
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Cliente

def send_email_async(subject, message, from_email, recipient_list):
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)

@receiver(post_save, sender=Cliente)
def send_welcome_email(sender, instance, created, **kwargs):
    if created:
        password = instance.last_name[:2] + instance.first_name[:2] + instance.phone_number[-4:]
        
        # Correo al administrador
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
                [os.environ.get('SENDER_EMAIL')]
            )
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
                ['ivanrdlt47@gmail.com']
            )
        ).start()
