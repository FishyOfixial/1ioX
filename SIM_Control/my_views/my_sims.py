from django.contrib.auth.decorators import login_required
from ..decorators import user_in
from ..models import SimCard, SIMQuota, SIMStatus, SIMAssignation, Distribuidor, Revendedor, User, UsuarioFinal
from ..utils import get_linked_users, get_assigned_iccids, log_user_action
from django.shortcuts import render, redirect
from ..api_client import update_sims_status
import json
from .translations import es, en, pt

LANG_MAP = {
    'es': (es.get_sims, es.base),
    'en': (en.get_sims, en.base),
    'pt': (pt.get_sims, pt.base)
}

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def get_sims(request):
    user = request.user
    lang, base = LANG_MAP.get(user.preferred_lang, LANG_MAP['es'])

    linked_users = get_linked_users(user)
    assigned_iccids = get_assigned_iccids(user)

    return render(request, 'get_sims.html', {
        'linked_users': linked_users,
        'lang': lang,
        'base': base,
    })

from django.http import JsonResponse

def get_sims_data(request):
    user = request.user

    linked_users = get_linked_users(user)
    assigned_iccids = get_assigned_iccids(user)
    priority = {"ONLINE": 0, "ATTACHED": 1, "OFFLINE": 2, "UNKNOWN": 3}

    sims_dict = SimCard.objects.in_bulk(assigned_iccids, field_name='iccid')
    quotas_dict = SIMQuota.objects.in_bulk(sims_dict.keys(), field_name='iccid')
    status_dict = SIMStatus.objects.in_bulk(sims_dict.keys(), field_name='iccid')

    assignations = {
        a.iccid.iccid: a
        for a in SIMAssignation.objects.filter(iccid__iccid__in=sims_dict.keys())
    }

    rows = []
    for iccid, sim in sims_dict.items():
        quota = quotas_dict.get(iccid)
        stat = status_dict.get(iccid)
        assignation = assignations.get(iccid)

        rows.append({
            'iccid': iccid,
            'isEnable': sim.status,
            'imei': sim.imei,
            'label': sim.label,
            'status': stat.status if stat else "UNKNOWN",
            'volume': float(quota.volume if quota else 0),
            'distribuidor': assignation.assigned_to_distribuidor.get_full_name() if assignation and assignation.assigned_to_distribuidor else '',
            'revendedor': assignation.assigned_to_revendedor.get_full_name() if assignation and assignation.assigned_to_revendedor else '',
            'cliente': assignation.assigned_to_usuario_final.get_full_name() if assignation and assignation.assigned_to_usuario_final else '',
            'whatsapp': assignation.assigned_to_usuario_final.get_phone_number() if assignation and assignation.assigned_to_usuario_final else '',
            'vehicle': assignation.assigned_to_vehicle.get_vehicle() if assignation and assignation.assigned_to_vehicle else '',
        })

    rows.sort(key=lambda r: priority.get(r["status"], 99))

    return JsonResponse({'rows': rows})


@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def assign_sims(request):
    if request.method != 'POST':
        return redirect('get_sims')

    user_id = request.POST.get('user_id')
    sim_ids = request.POST.getlist('sim_ids')
    user = User.objects.get(id=user_id)

    model_field_map = {
        'DISTRIBUIDOR': (Distribuidor, 'assigned_to_distribuidor'),
        'REVENDEDOR': (Revendedor, 'assigned_to_revendedor'),
        'FINAL': (UsuarioFinal, 'assigned_to_usuario_final'),
    }

    model, campo = model_field_map.get(user.user_type, (None, None))
    if not model or not campo:
        return redirect('get_sims')
    
    related_obj = model.objects.get(user_id=user.id)

    sim_objs = {sim.iccid: sim for sim in SimCard.objects.filter(iccid__in=sim_ids)}
    existing_assignations = SIMAssignation.objects.filter(iccid__iccid__in=sim_ids)
    assignation_map = {assign.iccid.iccid: assign for assign in existing_assignations}

    to_update = []
    to_create = []

    for iccid in sim_ids:
        sim_card = sim_objs.get(iccid)
        if not sim_card:
            continue

        sim_assign = assignation_map.get(iccid)
        if not sim_assign:
            sim_assign = SIMAssignation(iccid=sim_card)
            to_create.append(sim_assign)

        setattr(sim_assign, campo, related_obj)

        if user.user_type == 'FINAL':
            sim_assign.assigned_to_revendedor = related_obj.revendedor
            sim_assign.assigned_to_distribuidor = (
                related_obj.distribuidor or
                (related_obj.revendedor.distribuidor if related_obj.revendedor else None)
            )

            if sim_assign.assigned_to_vehicle:
                sim_assign.assigned_to_vehicle.usuario = related_obj
                sim_assign.assigned_to_vehicle.save()

        elif user.user_type == 'REVENDEDOR':
            sim_assign.assigned_to_distribuidor = related_obj.distribuidor

        if sim_assign not in to_create:
            to_update.append(sim_assign)

            log_user_action(request.user, 'SIMAssignation', 'ASSIGN', object_id=sim_card.id, description=f'{request.user} asigno la SIM: {sim_card.iccid} al usuario {user}')

    if to_create:
        SIMAssignation.objects.bulk_create(to_create)

    if to_update:
        fields = [campo]
        if user.user_type == 'FINAL':
            fields += ['assigned_to_revendedor', 'assigned_to_distribuidor']
        elif user.user_type == 'REVENDEDOR':
            fields += ['assigned_to_distribuidor']
        SIMAssignation.objects.bulk_update(to_update, fields)

    return redirect('get_sims')

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def update_sim_state(request):
    if request.method == "POST":
        try:
            status = request.POST.get("status", "Enabled")
            iccids = json.loads(request.POST.get("iccids", "[]"))
            labels = json.loads(request.POST.get("labels", "[]"))

            update_sims_status(iccids, labels, status)

            for iccid, label in zip(iccids, labels):
                sim = SimCard.objects.get(iccid=iccid)
                sim.label = label
                sim.status = status
                sim.save()

                log_user_action(request.user, 'SimCard', 'UPDATE', object_id=sim.id, description=f'{request.user} actualizó el estado de la SIM: {iccid} a {status}')

            return redirect("get_sims")
        except Exception as e:
            return redirect('get_sims')
    else:
        return redirect("get_sims")
