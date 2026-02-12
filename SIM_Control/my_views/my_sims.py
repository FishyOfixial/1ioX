from django.contrib.auth.decorators import login_required
from ..decorators import user_in
from ..models import SimCard, SIMQuota, SIMStatus, SIMAssignation, Distribuidor, Revendedor, User, Cliente
from ..utils import get_linked_users, get_assigned_sims, log_user_action
from django.shortcuts import render, redirect
from ..api_client import update_sims_status
import json
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage
from .translations import es, en, pt
from django.contrib.contenttypes.models import ContentType
from collections import defaultdict

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

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def get_sims_data(request):
    user = request.user
    has_offset_mode = "offset" in request.GET or "limit" in request.GET

    try:
        offset = int(request.GET.get("offset", 0))
    except (TypeError, ValueError):
        offset = 0
    offset = max(offset, 0)

    try:
        limit = int(request.GET.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50
    limit = min(max(limit, 1), 500)

    try:
        page = max(int(request.GET.get("page", 1)), 1)
    except (TypeError, ValueError):
        page = 1

    try:
        per_page = int(request.GET.get("per_page", 50))
    except (TypeError, ValueError):
        per_page = 50
    per_page = min(max(per_page, 1), 200)

    assigned_sims = get_assigned_sims(user)
    priority = {"ONLINE": 0, "ATTACHED": 1, "OFFLINE": 2, "UNKNOWN": 3}

    sims_qs = SimCard.objects.filter(iccid__in=assigned_sims).order_by('id')

    if has_offset_mode:
        total_count = sims_qs.count()
        sims = list(sims_qs[offset:offset + limit])

        sims_dict = {sim.iccid: sim for sim in sims}
        quotas = SIMQuota.objects.filter(sim__in=sims, quota_type='DATA')
        quotas_dict = {q.sim.iccid: q for q in quotas}
        statuses = SIMStatus.objects.filter(sim__in=sims)
        status_dict = {s.sim.iccid: s for s in statuses}

        assignations = defaultdict(list)
        for a in SIMAssignation.objects.filter(sim__in=sims).select_related('sim'):
            assignations[a.sim.iccid].append(a)

        rows = []
        for iccid, sim in sims_dict.items():
            quota = quotas_dict.get(iccid)
            stat = status_dict.get(iccid)
            assigns = assignations.get(iccid, [])

            distribuidor = revendedor = cliente = whatsapp = vehicle = ''

            for assignation in assigns:
                if not assignation.assigned_to:
                    continue

                assigned_obj = assignation.assigned_to
                model_name = assignation.content_type.model

                if model_name == "distribuidor":
                    distribuidor = assigned_obj.get_full_name()
                elif model_name == "revendedor":
                    revendedor = assigned_obj.get_full_name()
                elif model_name == "cliente":
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

        next_offset = offset + len(rows)
        has_more = next_offset < total_count

        return JsonResponse({
            'rows': rows,
            'offset': offset,
            'limit': limit,
            'next_offset': next_offset,
            'has_more': has_more,
            'total_count': total_count,
        })

    paginator = Paginator(sims_qs, per_page)

    if paginator.count == 0:
        return JsonResponse({
            'rows': [],
            'page': 1,
            'per_page': per_page,
            'total_pages': 1,
            'total_count': 0,
            'has_next': False,
            'has_prev': False,
        })

    try:
        sims_page = paginator.page(page)
    except EmptyPage:
        sims_page = paginator.page(paginator.num_pages)

    sims = list(sims_page.object_list)
    sims_dict = {sim.iccid: sim for sim in sims}
    quotas = SIMQuota.objects.filter(sim__in=sims, quota_type='DATA')
    quotas_dict = {q.sim.iccid: q for q in quotas}
    statuses = SIMStatus.objects.filter(sim__in=sims)
    status_dict = {s.sim.iccid: s for s in statuses}

    assignations = defaultdict(list)
    for a in SIMAssignation.objects.filter(sim__in=sims).select_related('sim'):
        assignations[a.sim.iccid].append(a)

    rows = []
    for iccid, sim in sims_dict.items():
        quota = quotas_dict.get(iccid)
        stat = status_dict.get(iccid)
        assigns = assignations.get(iccid, [])

        distribuidor = revendedor = cliente = whatsapp = vehicle = ''

        for assignation in assigns:
            if not assignation.assigned_to:
                continue

            assigned_obj = assignation.assigned_to
            model_name = assignation.content_type.model

            if model_name == "distribuidor":
                distribuidor = assigned_obj.get_full_name()
            elif model_name == "revendedor":
                revendedor = assigned_obj.get_full_name()
            elif model_name == "cliente":
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
    return JsonResponse({
        'rows': rows,
        'page': sims_page.number,
        'per_page': per_page,
        'total_pages': paginator.num_pages,
        'total_count': paginator.count,
        'has_next': sims_page.has_next(),
        'has_prev': sims_page.has_previous(),
    })

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

    assign_targets = [related_obj]
    if user.user_type == 'CLIENTE':
        if related_obj.revendedor:
            assign_targets.append(related_obj.revendedor)
        if related_obj.distribuidor:
            assign_targets.append(related_obj.distribuidor)
    elif user.user_type == 'REVENDEDOR' and related_obj.distribuidor:
        assign_targets.append(related_obj.distribuidor)

    sim_objs = {sim.iccid: sim for sim in SimCard.objects.filter(iccid__in=sim_ids)}

    existing_assignations = SIMAssignation.objects.filter(sim__iccid__in=sim_ids)
    assignation_map = {
        (assign.sim.iccid, assign.content_type_id, assign.object_id): assign
        for assign in existing_assignations
    }

    to_create = []
    to_update = []

    for iccid in sim_ids:
        sim_card = sim_objs.get(iccid)
        if not sim_card:
            continue

        for target in assign_targets:
            ct_target = ContentType.objects.get_for_model(target.__class__)
            key = (iccid, ct_target.id, target.id)

            if key in assignation_map:
                assign = assignation_map[key]

                assign.object_id = target.id
                assign.content_type = ct_target
                to_update.append(assign)
            else:

                assign = SIMAssignation(sim=sim_card, content_type=ct_target, object_id=target.id)
                to_create.append(assign)
                assignation_map[key] = assign

            log_user_action(
                request.user,
                'SIMAssignation',
                'ASSIGN',
                object_id=sim_card.id,
                description=f'{request.user} asignó la SIM: {sim_card.iccid} al usuario {target.get_full_name()}'
            )

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
