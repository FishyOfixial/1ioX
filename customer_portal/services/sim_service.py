from django.contrib.contenttypes.models import ContentType

from SIM_Control.models import Cliente, SIMAssignation, SimCard


def get_client_sims(user):
    cliente = Cliente.objects.filter(user=user).first()
    if not cliente:
        return SimCard.objects.none()

    client_type = ContentType.objects.get_for_model(Cliente)
    sim_ids = SIMAssignation.objects.filter(
        content_type=client_type,
        object_id=cliente.id,
        sim__isnull=False,
    ).values_list("sim_id", flat=True)

    return SimCard.objects.filter(id__in=sim_ids).distinct().order_by("iccid")