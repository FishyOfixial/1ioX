from django.db.models.signals import post_save
from .models import UsuarioFinal
from django.dispatch import receiver
from django.core.mail import send_mail
import os

SENDER_EMAIL = os.environ.get('SENDER_EMAIL')

@receiver(post_save, sender=UsuarioFinal)
def send_welcome_email(sender, instance, created, **kwargs):
    if created:
        password = (instance.last_name[:2] + instance.first_name[:2] + instance.phone_number[-4:])
        send_mail(
            subject='¡Se ha registrado a un nuevo cliente!',
            message = f"""
                Se ha registrado a {instance.get_full_name()}
                Empresa: {instance.company}
                Ciudad: {instance.city}, {instance.state}
                Teléfono: {instance.phone_number}
                Correo: {instance.email}
                Contraseña: {password}
                """,
            from_email=os.environ.get('SENDER_EMAIL'),
            recipient_list=os.environ.get('SENDER_EMAIL'),
        )