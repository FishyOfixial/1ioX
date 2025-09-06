from django.contrib.auth.decorators import login_required
from ..decorators import user_in
from ..models import SimCard, SIMQuota, SIMStatus, SIMAssignation, Distribuidor, Revendedor, User, Cliente
from ..utils import get_linked_users, get_assigned_sims, log_user_action
from django.shortcuts import render, redirect
from ..api_client import update_sims_status
import json
from django.http import JsonResponse
from .translations import es, en, pt
from django.contrib.contenttypes.models import ContentType

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
    return render(request, 'get_sims.html', {
        'linked_users': linked_users,
        'lang': lang,
        'base': base,
    })

def get_sims_data(request):
    user = request.user

    assigned_sims = get_assigned_sims(user)
    priority = {"ONLINE": 0, "ATTACHED": 1, "OFFLINE": 2, "UNKNOWN": 3}

    sims = SimCard.objects.filter(id__in=assigned_sims)
    sims_dict = {sim.iccid: sim for sim in sims}
    quotas = SIMQuota.objects.filter(sim__in=sims, quota_type='DATA')
    quotas_dict = {q.sim.iccid: q for q in quotas}
    statuses = SIMStatus.objects.filter(sim__in=sims)
    status_dict = {s.sim.iccid: s for s in statuses}

    assignations = {
        a.sim.iccid: a
        for a in SIMAssignation.objects.filter(sim__in=sims)
    }
    rows = []
    for iccid, sim in sims_dict.items():
        quota = quotas_dict.get(iccid)
        stat = status_dict.get(iccid)
        assignation = assignations.get(iccid)

        distribuidor = revendedor = cliente = whatsapp = vehicle = ''
        if assignation and assignation.assigned_to:
            assigned_obj = assignation.assigned_to
            model_name = assignation.content_type.model

            if model_name == "distribuidor":
                distribuidor = assigned_obj.get_full_name()
            elif model_name == "revendedor":
                revendedor = assigned_obj.get_full_name()
            elif model_name == "usuariofinal":
                cliente = assigned_obj.get_full_name()
                if hasattr(assigned_obj, "get_phone_number"):
                    whatsapp = assigned_obj.get_phone_number()
            elif model_name == "vehicle":
                if hasattr(assigned_obj, "get_vehicle"):
                    vehicle = assigned_obj.get_vehicle()

        rows.append({
            'iccid': iccid,
            'isEnable': sim.status,
            'imei': sim.imei,
            'label': sim.label,
            'status': stat.status if stat else "UNKNOWN",
            'volume': float(quota.volume if quota else 0),
            'distribuidor': distribuidor,
            'revendedor': revendedor,
            'cliente': cliente,
            'whatsapp': whatsapp,
            'vehicle': vehicle,
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

    model_map = {
        'DISTRIBUIDOR': Distribuidor,
        'REVENDEDOR': Revendedor,
        'CLIENTE': Cliente,
    }

    model = model_map.get(user.user_type)
    if not model:
        return redirect('get_sims')
    
    related_obj = model.objects.get(user=user)
    ct = ContentType.objects.get_for_model(model)

    sim_objs = {sim.iccid: sim for sim in SimCard.objects.filter(iccid__in=sim_ids)}
    existing_assignations = SIMAssignation.objects.filter(sim__iccid__in=sim_ids)
    assignation_map = {assign.sim.iccid: assign for assign in existing_assignations}

    to_update = []
    to_create = []

    for iccid in sim_ids:
        sim_card = sim_objs.get(iccid)
        if not sim_card:
            continue

        sim_assign = assignation_map.get(iccid)
        if not sim_assign:
            sim_assign = SIMAssignation(sim=sim_card)
            to_create.append(sim_assign)

        sim_assign.content_type = ct
        sim_assign.object_id = related_obj.id

        if sim_assign not in to_create:
            to_update.append(sim_assign)

        log_user_action(request.user, 'SIMAssignation', 'ASSIGN', object_id=sim_card.id, description=f'{request.user} asigno la SIM: {sim_card.iccid} al usuario {user}')

    if to_create:
        SIMAssignation.objects.bulk_create(to_create)

    if to_update:
        SIMAssignation.objects.bulk_update(to_update, ['content_type', 'object_id'])

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
