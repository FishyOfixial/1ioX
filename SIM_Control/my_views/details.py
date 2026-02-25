from datetime import timedelta

from ..decorators import user_in, matriz_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from ..utils import get_assigned_sims, get_or_fetch_sms, get_or_fetch_location, log_user_action
from ..models import *
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponseForbidden, Http404, JsonResponse
from django.db.models import Q
from django.db import transaction
from ..api_client import update_sim_label, send_sms_api
from operator import attrgetter
from .translations import get_translation
from django.views.decorators.http import require_GET
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from billing.models import MembershipPlan

@matriz_required
def order_details(request, order_number):
    order = get_object_or_404(Order.objects.select_related('shipping_address'), order_number=order_number)

    order_sims = list(OrderSIM.objects.filter(order_id=order.id))
    mid = len(order_sims)//2
    order_one = order_sims[:mid]
    order_two = order_sims[mid:]

    total_sims = len(order_sims)

    context = {
        'order': order,
        'order_sims': order_sims,
        'total_sims': total_sims,
        'shipping_address': order.shipping_address,
        'order_one': order_one,
        'order_two': order_two
    }

    return render(request, 'order_details.html', context)

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def sim_details(request, iccid):
    user = request.user
    lang, base = get_translation(user, "sim_details")

    sim = get_object_or_404(SimCard, iccid=iccid)
    assigned_sims = get_assigned_sims(user)

    if sim.iccid not in assigned_sims:
        return HttpResponseForbidden("No tienes permiso para ver esta SIM.")
    
    distribuidor = None
    revendedor = None
    client = None
    vehicle = None

    assignations = SIMAssignation.objects.filter(sim=sim).select_related('content_type')
    for assignation in assignations:
        if assignation.assigned_to:
            assigned_obj = assignation.assigned_to
            model_name = assignation.content_type.model

            if model_name == "vehicle":
                vehicle = assigned_obj
            elif model_name == "cliente":
                client = assigned_obj
            elif model_name == 'distribuidor':
                distribuidor = assigned_obj
            elif model_name == 'revendedor':
                revendedor = assigned_obj

    data_quota = sim.quotas.filter(quota_type='DATA').first()
    sms_quota = sim.quotas.filter(quota_type='SMS').first()
    status = SIMStatus.objects.filter(sim=sim).first()

    monthly_usage = MonthlySimUsage.objects.filter(sim=sim).order_by('-month')[:6]
    monthly_usage = sorted(monthly_usage, key=attrgetter('month'))
    
    commands = CommandRunLog.objects.filter(command_name__in=[
    'actual_usage', 'update_data_quotas', 'update_sms_quotas'
    ])
    commands_dict = {cmd.command_name: cmd for cmd in commands}

    data_volume = data_quota.volume if data_quota else 0
    data_used = (data_quota.total_volume - data_volume) if data_quota else 0
    sms_volume = sms_quota.volume if sms_quota else 0
    sms_used = (sms_quota.total_volume - sms_volume) if sms_quota else 0

    monthly_use = [
        {
            'month': mu.month,
            'data_used': mu.data_volume,
            'sms_used': mu.sms_volume
        }
        for mu in monthly_usage
    ]

    sms_list = get_or_fetch_sms(sim)
    current_subscription = sim.current_subscription
    membership_plans = (
        MembershipPlan.objects.filter(is_active=True)
        .exclude(name__istartswith="Custom ")
        .order_by("duration_days")
    )
    expiring_soon = False
    if current_subscription:
        expiring_soon = current_subscription.end_date <= timezone.now() + timedelta(days=7)
    
    context = {
        'sim': sim,
        'assignation': {
            'distribuidor': distribuidor,
            'revendedor': revendedor,
        },
        'data_quota': data_quota,
        'sms_quota': sms_quota,
        'status': status,
        'sms_list': sms_list,
        'all_comands': {
            'monthly_usage': commands_dict.get('actual_usage'),
            'data_quota': commands_dict.get('update_data_quotas'),
            'sms_quota': commands_dict.get('update_sms_quotas'),
        },
        'chart_data': {
            'data_volume': data_volume,
            'data_used': data_used,
            'sms_volume': sms_volume,
            'sms_used': sms_used,
            'monthly_use': monthly_use,
        },
        'vehicle': vehicle,
        'client':  client,
        'current_subscription': current_subscription,
        'membership_plans': membership_plans,
        'expiring_soon': expiring_soon,
        'lang': lang,
        'base': base
    }
        
    return render(request, 'sim_details.html', context)

@login_required
@require_GET
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def api_get_sim_location(request, iccid):
    #get_or_fetch_location(iccid)
    sim = SimCard.objects.filter(iccid=iccid).first()
    if not sim:
        return JsonResponse({'error': 'SIM no encontrada'}, status=404)
    if request.user.user_type in ["DISTRIBUIDOR", "REVENDEDOR"] and sim.iccid not in get_assigned_sims(request.user):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    location = SIMLocation.objects.filter(sim=sim).first()
    if not location:
        return JsonResponse({'error': 'Ubicación no disponible'}, status=404)

    data = {
        'latitude': location.latitude,
        'longitude': location.longitude,
        'sample_time': location.sample_time.isoformat() if location.sample_time else None,
    }
    return JsonResponse(data)

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def update_label(request, iccid):
    if request.method != "POST":
        return redirect("sim_details", iccid)

    try:
        sim = get_object_or_404(SimCard, iccid=iccid)
        if sim.iccid not in get_assigned_sims(request.user):
            return HttpResponseForbidden("No tienes permiso para actualizar esta SIM.")

        client_name = (request.POST.get("client_name") or "").strip()
        company_name = (request.POST.get("company_name") or "").strip()
        brand = (request.POST.get("brand") or "").strip()
        model = (request.POST.get("model") or "").strip()
        year_raw = (request.POST.get("year") or "").strip()
        color = (request.POST.get("color") or "").strip()
        buy_date = (request.POST.get("buy_date") or "").strip()
        unit_number = (request.POST.get("unit_number") or "").strip()
        status = (request.POST.get("status") or sim.status or "").strip()

        vehicle_label = " ".join(part for part in [brand, model, year_raw, color] if part).strip()
        label = "-".join(part for part in [client_name, company_name, vehicle_label, buy_date] if part).strip()
        year = int(year_raw) if year_raw.isdigit() else None

        client_assignation = SIMAssignation.objects.filter(
            sim=sim,
            content_type__model='cliente'
        ).select_related('content_type').first()
        client_obj = client_assignation.assigned_to if client_assignation else None

        with transaction.atomic():
            update_sim_label(iccid, label, status)

            vehicle_obj, created = Vehicle.objects.update_or_create(
                sim=sim,
                defaults={
                    'brand': brand,
                    'model': model,
                    'year': year,
                    'color': color,
                    'unit_number': unit_number,
                    'cliente': client_obj if isinstance(client_obj, Cliente) else None,
                    'imei_gps': sim.imei,
                }
            )

            log_user_action(
                request.user,
                'Vehicle',
                'CREATE' if created else 'UPDATE',
                object_id=vehicle_obj.id,
                description=f'{request.user} registro/actualizo un vehiculo'
            )

            sim.label = label
            sim.status = status
            sim.save(update_fields=['label', 'status'])
            log_user_action(
                request.user,
                'SimCard',
                'UPDATE',
                object_id=sim.id,
                description=f'{request.user} actualizo la etiqueta de la SIM: {iccid} a ("{label}")'
            )

            vehicle_ct = ContentType.objects.get_for_model(Vehicle)
            SIMAssignation.objects.update_or_create(
                sim=sim,
                content_type=vehicle_ct,
                object_id=vehicle_obj.id,
                defaults={}
            )

            if isinstance(client_obj, Cliente):
                client_ct = ContentType.objects.get_for_model(Cliente)
                SIMAssignation.objects.update_or_create(
                    sim=sim,
                    content_type=client_ct,
                    object_id=client_obj.id,
                    defaults={}
                )

        return redirect("sim_details", iccid)
    except Exception as e:
        print(e)
        return redirect('sim_details', iccid)

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def send_sms(request, iccid):
    if request.method == 'POST':
        try:
            source = (request.POST.get('source') or '').strip()
            commands = request.POST.get('command') or ''
            command_list = [line.strip() for line in commands.strip().split('\n') if line.strip()]
            
            for command in command_list:
                send_sms_api(iccid, source, command)
                log_user_action(request.user, 'SMSMessage', 'SEND_SMS', description=f'{request.user} envió un mensaje a: {iccid}')

            return redirect("sim_details", iccid)
        except Exception as e:
            print(e)
            return redirect('get_sims')
    else:
        return redirect('sim_details', iccid)

@login_required
@user_in('DISTRIBUIDOR', 'REVENDEDOR')
def user_details(request, type, id):
    user = request.user
    lang, base = get_translation(user, "user_details")
    user_type = user.user_type
    
    linked_revendedor = []
    linked_final = []
    linked_sims = []
    linked_vehicles = []

    model_map = {
        'DISTRIBUIDOR': Distribuidor,
        'REVENDEDOR': Revendedor,
        'CLIENTE': Cliente
    }

    type_upper = type.upper()
    if type_upper not in model_map:
        raise Http404()

    ModelClass = model_map[type_upper]
    
    if user_type == 'MATRIZ':
        details = get_object_or_404(ModelClass, id=id)

        if type_upper == 'DISTRIBUIDOR':
            linked_revendedor = Revendedor.objects.filter(distribuidor=details)
            linked_final = Cliente.objects.filter(Q(distribuidor=details) | Q(revendedor__distribuidor=details))
            linked_sims = get_assigned_sims(details.user, with_label=True)

        elif type_upper == 'REVENDEDOR':
            linked_final = Cliente.objects.filter(revendedor=details)
            linked_sims = get_assigned_sims(details.user, with_label=True)

        elif type_upper == 'CLIENTE':
            linked_sims = get_assigned_sims(details.user, with_label=True)
            linked_vehicles = [vehicle.get_vehicle() for vehicle in Vehicle.objects.filter(cliente=details)]

    elif user_type == 'DISTRIBUIDOR':
        distribuidor = Distribuidor.objects.get(user=user)

        if type_upper == 'REVENDEDOR':
            details = get_object_or_404(Revendedor, id=id, distribuidor=distribuidor)
            linked_final = Cliente.objects.filter(revendedor=details)
            linked_sims = get_assigned_sims(details.user, with_label=True)

        elif type_upper == 'CLIENTE':
            details = get_object_or_404(Cliente, Q(distribuidor=distribuidor) | Q(revendedor__distribuidor=distribuidor), id=id)
            linked_sims = get_assigned_sims(details.user, with_label=True)
            linked_vehicles = [vehicle.get_vehicle() for vehicle in Vehicle.objects.filter(cliente=details)]

        else:
            raise Http404()

    elif user_type == 'REVENDEDOR':
        revendedor = Revendedor.objects.get(user=user)

        if type_upper == 'CLIENTE':
            details = get_object_or_404(Cliente, revendedor=revendedor, id=id)
            linked_sims = get_assigned_sims(details.user, with_label=True)
            linked_vehicles = [vehicle.get_vehicle() for vehicle in Vehicle.objects.filter(cliente=details)]
        else:
            raise Http404()
    else:
        raise Http404()

    mid_sim = len(linked_sims)//2 if linked_sims else 0
    mid_veh = len(linked_vehicles)//2 if linked_vehicles else 0
    is_active = details.user.is_active

    return render(request, 'user_details.html', {
        'user': details,
        'type': type.lower(),
        'can_change_password': request.user.user_type == 'MATRIZ',
        'linked_revendedor': linked_revendedor,
        'linked_final': linked_final,
        'linked_sims_one': linked_sims[:mid_sim],
        'linked_sims_two': linked_sims[mid_sim:],
        'vehicles_one': linked_vehicles[:mid_veh],
        'vehicles_two': linked_vehicles[mid_veh:],
        'total_sims': len(linked_sims),
        'is_active': is_active,
        'lang': lang,
        'base': base,
    })

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def update_user_account(request, user_id):
    if request.method == "POST":
        try:            
            action = request.POST.get("action")
            user = User.objects.get(id=user_id)

            if action == "active":
                log_user_action(request.user, 'User', 'DISABLE' if user.is_active else 'ENABLE', object_id=user.id,
                                description=f'{request.user} deshabilito al usuario {user}' if user.is_active else f'{request.user} habilito al usuario {user}')
                user.is_active = not user.is_active
                user.save()
            
            elif action == "delete":
                log_user_action(request.user, 'User', 'DELETE', object_id=user.id, description=f'{request.user} elimino al usuario {user}')
                user.delete()

            return redirect("get_users")
        except Exception as e:
            return render(request, "error.html", {"error": str(e)})
    else:
        return redirect("get_users")

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def update_user(request, user_id):
    if request.method != 'POST':
        return redirect('get_users')
    is_async_request = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    
    user_obj = get_object_or_404(User, id=user_id)
    user_type_model_map = {
        'DISTRIBUIDOR': Distribuidor,
        'REVENDEDOR': Revendedor,
        'CLIENTE': Cliente,
    }

    model = user_type_model_map.get(user_obj.user_type)
    if not model:
        raise Http404()
    
    related_obj = model.objects.get(user=user_obj)
    first_name = (request.POST.get("first_name") or "").strip()
    last_name = (request.POST.get("last_name") or "").strip()
    email = (request.POST.get("email") or "").strip().lower()
    phone = (request.POST.get("phone_number") or "").strip()
    rfc = (request.POST.get('rfc') or "").strip()

    if User.objects.filter(email=email).exclude(id=user_id).exists():
        error_msg = "El correo ya está registrado."
        if is_async_request:
            return JsonResponse({"ok": False, "error": error_msg}, status=400)
        messages.error(request, error_msg)
        return redirect('user_details', type=user_obj.user_type, id=related_obj.id)

    user_obj.username = email
    user_obj.first_name = first_name
    user_obj.last_name = last_name
    user_obj.email = email
    
    new_password = (request.POST.get("new_password") or "").strip()
    confirm_password = (request.POST.get("confirm_password") or "").strip()
    password_changed = False

    if new_password or confirm_password:
        if request.user.user_type != "MATRIZ":
            error_msg = "Solo MATRIZ puede cambiar contraseñas."
            if is_async_request:
                return JsonResponse({"ok": False, "error": error_msg}, status=403)
            messages.error(request, error_msg)
            return redirect('user_details', type=user_obj.user_type, id=related_obj.id)

        if new_password != confirm_password:
            error_msg = "La confirmación de contraseña no coincide."
            if is_async_request:
                return JsonResponse({"ok": False, "error": error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect('user_details', type=user_obj.user_type, id=related_obj.id)

        try:
            validate_password(new_password, user=user_obj)
        except ValidationError as e:
            error_msg = " ".join(e.messages)
            if is_async_request:
                return JsonResponse({"ok": False, "error": error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect('user_details', type=user_obj.user_type, id=related_obj.id)

        user_obj.set_password(new_password)
        password_changed = True

    user_obj.save()
    if password_changed and request.user.id == user_obj.id:
        update_session_auth_hash(request, user_obj)

    fields_to_update = [
        'first_name', 'last_name', 'email', 'phone_number', 'company', 'rfc', 'street', 
        'city', 'zip', 'state', 'country'
    ]

    for field in fields_to_update:
        if hasattr(related_obj, field):
            setattr(related_obj, field, request.POST.get(field, getattr(related_obj, field)))

    log_user_action(request.user, model.__name__, 'UPDATE', object_id=user_obj.id, description=f'{request.user} actualizó los datos de {user_obj}')
    related_obj.save()

    if is_async_request:
        return JsonResponse({
            "ok": True,
            "message": "Usuario actualizado correctamente.",
            "password_changed": password_changed,
        })

    return redirect('user_details', user_obj.user_type, related_obj.id)
