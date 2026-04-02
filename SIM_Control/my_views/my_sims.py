from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from ..decorators import user_in
from ..models import SimCard, SIMQuota, SIMStatus, SIMAssignation, Distribuidor, Revendedor, User, Cliente
from ..utils import (
    get_assigned_sims,
    get_linked_users,
    get_manageable_sims_or_raise,
    get_manageable_user_or_raise,
    get_sim_list_cache_version,
    invalidate_sim_list_cache_for_sim_ids,
    log_user_action,
)
from django.shortcuts import render, redirect
from ..api_client import update_sims_status
import json
from django.http import Http404, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.core.paginator import Paginator, EmptyPage
from .translations import get_translation
from django.contrib.contenttypes.models import ContentType
from collections import defaultdict
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from billing.models import Subscription

SIM_LIST_CACHE_TTL_SECONDS = 30
SIM_LIST_INITIAL_LIMIT_DEFAULT = 50


def _normalize_sim_list_request(request):
    has_offset_mode = "offset" in request.GET or "limit" in request.GET

    try:
        offset = int(request.GET.get("offset", 0))
    except (TypeError, ValueError):
        offset = 0
    offset = max(offset, 0)

    try:
        limit = int(request.GET.get("limit", SIM_LIST_INITIAL_LIMIT_DEFAULT))
    except (TypeError, ValueError):
        limit = SIM_LIST_INITIAL_LIMIT_DEFAULT
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

    return has_offset_mode, offset, limit, page, per_page


def _build_sim_list_cache_key(user_id, *, offset, limit, page, per_page, has_offset_mode):
    mode = "offset" if has_offset_mode else "page"
    version = get_sim_list_cache_version(user_id)
    return f"sim-list:{user_id}:v{version}:{mode}:{offset}:{limit}:{page}:{per_page}"


def _get_paginated_rows(sims_qs, *, offset, limit, page, per_page, has_offset_mode, priority, current_time):
    if has_offset_mode:
        total_count = sims_qs.count()
        sims_page = list(sims_qs[offset:offset + limit])
    else:
        paginator = Paginator(sims_qs, per_page)

        if paginator.count == 0:
            return {
                "rows": [],
                "page": 1,
                "per_page": per_page,
                "total_pages": 1,
                "total_count": 0,
                "has_next": False,
                "has_prev": False,
            }

        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        sims_page = list(page_obj.object_list)
        total_count = paginator.count

    sim_ids = [sim["id"] for sim in sims_page]
    sim_iccids = [sim["iccid"] for sim in sims_page]
    sim_by_id = {sim["id"]: sim for sim in sims_page}
    sim_id_by_iccid = {sim["iccid"]: sim["id"] for sim in sims_page}

    quota_rows = SIMQuota.objects.filter(sim_id__in=sim_ids, quota_type="DATA").values("sim_id", "volume")
    quotas_by_sim_id = {row["sim_id"]: float(row["volume"] or 0) for row in quota_rows}

    status_rows = SIMStatus.objects.filter(sim_id__in=sim_ids).values("sim_id", "status")
    statuses_by_sim_id = {row["sim_id"]: row["status"] for row in status_rows}

    latest_subscriptions = {}
    subs_qs = (
        Subscription.objects.filter(sim_id__in=sim_ids)
        .order_by("sim_id", "-created_at")
        .values("sim_id", "status", "end_date")
    )
    for sub in subs_qs:
        if sub["sim_id"] not in latest_subscriptions:
            latest_subscriptions[sub["sim_id"]] = sub

    client_content_type = ContentType.objects.get_for_model(Cliente)
    distribuidor_content_type = ContentType.objects.get_for_model(Distribuidor)
    revendedor_content_type = ContentType.objects.get_for_model(Revendedor)

    assignation_rows = list(
        SIMAssignation.objects.filter(sim_id__in=sim_ids).values("sim_id", "content_type_id", "object_id")
    )

    cliente_ids = {row["object_id"] for row in assignation_rows if row["content_type_id"] == client_content_type.id}
    distribuidor_ids = {row["object_id"] for row in assignation_rows if row["content_type_id"] == distribuidor_content_type.id}
    revendedor_ids = {row["object_id"] for row in assignation_rows if row["content_type_id"] == revendedor_content_type.id}

    clientes = {
        row["id"]: row
        for row in Cliente.objects.filter(id__in=cliente_ids).values("id", "first_name", "last_name", "phone_number")
    }
    distribuidores = {
        row["id"]: row
        for row in Distribuidor.objects.filter(id__in=distribuidor_ids).values("id", "first_name", "last_name")
    }
    revendedores = {
        row["id"]: row
        for row in Revendedor.objects.filter(id__in=revendedor_ids).values("id", "first_name", "last_name")
    }

    assignations_by_sim_id = defaultdict(dict)
    for row in assignation_rows:
        assignations_by_sim_id[row["sim_id"]][row["content_type_id"]] = row["object_id"]

    rows = []
    for iccid in sim_iccids:
        sim_id = sim_id_by_iccid[iccid]
        sim = sim_by_id[sim_id]
        assignation_ids = assignations_by_sim_id.get(sim_id, {})

        distribuidor = distribuidores.get(assignation_ids.get(distribuidor_content_type.id))
        revendedor = revendedores.get(assignation_ids.get(revendedor_content_type.id))
        cliente = clientes.get(assignation_ids.get(client_content_type.id))

        imei = sim["vehicle__imei_gps"] or sim["imei"]
        subscription_status = "none"
        sub_info = latest_subscriptions.get(sim_id)
        if sub_info:
            subscription_status = sub_info["status"] or "none"
            if subscription_status == "active" and sub_info["end_date"] and sub_info["end_date"] < current_time:
                subscription_status = "expired"

        rows.append({
            "iccid": iccid,
            "isEnable": sim["status"],
            "imei": imei,
            "label": sim["label"],
            "status": statuses_by_sim_id.get(sim_id, "UNKNOWN"),
            "subscription_status": subscription_status,
            "volume": quotas_by_sim_id.get(sim_id, 0.0),
            "distribuidor": f"{distribuidor['first_name']} {distribuidor['last_name']}".strip() if distribuidor else "",
            "revendedor": f"{revendedor['first_name']} {revendedor['last_name']}".strip() if revendedor else "",
            "cliente": f"{cliente['first_name']} {cliente['last_name']}".strip() if cliente else "",
            "whatsapp": cliente["phone_number"] if cliente else "",
            "vehicle": "",
        })

    rows.sort(key=lambda r: priority.get(r["status"], 99))

    if has_offset_mode:
        next_offset = offset + len(rows)
        return {
            "rows": rows,
            "offset": offset,
            "limit": limit,
            "next_offset": next_offset,
            "has_more": next_offset < total_count,
            "total_count": total_count,
        }

    return {
        "rows": rows,
        "page": page_obj.number,
        "per_page": per_page,
        "total_pages": paginator.num_pages,
        "total_count": paginator.count,
        "has_next": page_obj.has_next(),
        "has_prev": page_obj.has_previous(),
    }

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def get_sims(request):
    user = request.user
    lang, base = get_translation(user, "get_sims")

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
    has_offset_mode, offset, limit, page, per_page = _normalize_sim_list_request(request)
    cache_key = _build_sim_list_cache_key(
        user.id,
        offset=offset,
        limit=limit,
        page=page,
        per_page=per_page,
        has_offset_mode=has_offset_mode,
    )
    try:
        cached_response = cache.get(cache_key)
    except Exception:
        cached_response = None
    if cached_response is not None:
        return JsonResponse(cached_response)

    assigned_sims = get_assigned_sims(user)
    priority = {"ONLINE": 0, "ATTACHED": 1, "OFFLINE": 2, "UNKNOWN": 3}
    current_time = timezone.now()

    sims_qs = (
        SimCard.objects.filter(iccid__in=assigned_sims)
        .order_by("id")
        .values("id", "iccid", "status", "label", "imei", "vehicle__imei_gps")
    )
    response_payload = _get_paginated_rows(
        sims_qs,
        offset=offset,
        limit=limit,
        page=page,
        per_page=per_page,
        has_offset_mode=has_offset_mode,
        priority=priority,
        current_time=current_time,
    )
    try:
        cache.set(cache_key, response_payload, SIM_LIST_CACHE_TTL_SECONDS)
    except Exception:
        pass
    return JsonResponse(response_payload)

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def assign_sims(request):
    if request.method != 'POST':
        return redirect('get_sims')

    user_id = (request.POST.get('user_id') or "").strip()
    sim_ids = request.POST.getlist('sim_ids')
    if not user_id.isdigit():
        raise Http404("Usuario no encontrado.")

    user = User.objects.filter(id=int(user_id)).first()
    if user is None:
        raise Http404("Usuario no encontrado.")

    try:
        get_manageable_user_or_raise(request.user, user)
        authorized_sims = get_manageable_sims_or_raise(request.user, sim_ids)
    except PermissionDenied as exc:
        return HttpResponseForbidden(str(exc))
    except SimCard.DoesNotExist:
        raise Http404("SIM no encontrada.")

    model_map = {
        'DISTRIBUIDOR': Distribuidor,
        'REVENDEDOR': Revendedor,
        'CLIENTE': Cliente,
    }

    model = model_map.get(user.user_type)
    if not model:
        raise Http404("Usuario no encontrado.")
    
    related_obj = model.objects.get(user=user)

    assign_targets = [related_obj]
    if user.user_type == 'CLIENTE':
        if related_obj.revendedor:
            assign_targets.append(related_obj.revendedor)
        if related_obj.distribuidor:
            assign_targets.append(related_obj.distribuidor)
    elif user.user_type == 'REVENDEDOR' and related_obj.distribuidor:
        assign_targets.append(related_obj.distribuidor)

    sim_objs = {sim.iccid: sim for sim in authorized_sims}

    authorized_iccids = [sim.iccid for sim in authorized_sims]
    existing_assignations = SIMAssignation.objects.filter(sim__iccid__in=authorized_iccids)
    assignation_map = {
        (assign.sim.iccid, assign.content_type_id, assign.object_id): assign
        for assign in existing_assignations
    }

    to_create = []
    to_update = []

    for iccid in authorized_iccids:
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
        SIMAssignation.objects.bulk_create(to_create, ignore_conflicts=True)
    if to_update:
        SIMAssignation.objects.bulk_update(to_update, ['content_type', 'object_id'])
    invalidate_sim_list_cache_for_sim_ids([sim.id for sim in authorized_sims])

    return redirect('get_sims')

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def update_sim_state(request):
    if request.method == "POST":
        try:
            status = request.POST.get("status", "Enabled")
            iccids = json.loads(request.POST.get("iccids", "[]"))
            labels = json.loads(request.POST.get("labels", "[]"))
            if not isinstance(iccids, list) or not isinstance(labels, list) or len(iccids) != len(labels):
                return HttpResponseBadRequest("Solicitud invalida.")

            authorized_sims = get_manageable_sims_or_raise(request.user, iccids)
            labels_by_iccid = {str(iccid).strip(): label for iccid, label in zip(iccids, labels)}
            authorized_iccids = [sim.iccid for sim in authorized_sims]
            authorized_labels = [labels_by_iccid.get(iccid, "") for iccid in authorized_iccids]
            update_sims_status(authorized_iccids, authorized_labels, status)

            for iccid, label in zip(authorized_iccids, authorized_labels):
                sim = next((current_sim for current_sim in authorized_sims if current_sim.iccid == iccid), None)
                if sim is None:
                    continue
                sim.label = label
                sim.status = status
                sim.save()

            invalidate_sim_list_cache_for_sim_ids([sim.id for sim in authorized_sims])

            return redirect("get_sims")
        except PermissionDenied as exc:
            return HttpResponseForbidden(str(exc))
        except SimCard.DoesNotExist:
            raise Http404("SIM no encontrada.")
        except Exception as e:
            return redirect('get_sims')
    else:
        return redirect("get_sims")
