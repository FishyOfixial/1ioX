from ..decorators import user_in
from django.contrib.auth.decorators import login_required, user_passes_test
from ..utils import is_matriz, get_assigned_sims, get_or_fetch_sms, get_or_fetch_location, log_user_action
from ..models import *
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponseForbidden, Http404, JsonResponse
from django.db.models import Q
from ..api_client import update_sim_label, send_sms_api
from operator import attrgetter
from .translations import en, es, pt
from django.views.decorators.http import require_GET
from django.core.mail import send_mail
import os, threading
from django.contrib import messages

LANG_SIM = {
    'es': (es.sim_details, es.base),
    'en': (en.sim_details, en.base),
    'pt': (pt.sim_details, pt.base)
}

LANG_USER = {
    'es': (es.user_details, es.base),
    'en': (en.user_details, en.base),
    'pt': (pt.user_details, pt.base)
}

SENDER_EMAIL = os.environ.get('SENDER_EMAIL')

@login_required
@user_passes_test(is_matriz)
def order_details(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)

    order_sims = OrderSIM.objects.filter(order_id=order.id)
    mid = len(order_sims)//2
    order_one = order_sims[:mid]
    order_two = order_sims[mid:]

    total_sims = order_sims.count()
    shipping_address = ShippingAddress.objects.get(id=order.shipping_address_id)

    context = {
        'order': order,
        'order_sims': order_sims,
        'total_sims': total_sims,
        'shipping_address': shipping_address,
        'order_one': order_one,
        'order_two': order_two
    }

    return render(request, 'order_details.html', context)

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def sim_details(request, iccid):
    user = request.user
    lang, base = LANG_SIM.get(user.preferred_lang, LANG_SIM['es'])

    sim = get_object_or_404(SimCard, iccid=iccid)
    assigned_sims = get_assigned_sims(user)

    if sim.iccid not in assigned_sims:
        return HttpResponseForbidden("No tienes permiso para ver esta SIM.")
    
    distribuidor = None
    revendedor = None
    client = None
    vehicle = None

    assignations = SIMAssignation.objects.filter(sim=sim)
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
    status = SIMStatus.objects.get(sim=sim)

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
        'lang': lang,
        'base': base
    }
        
    return render(request, 'sim_details.html', context)

@login_required
@require_GET
def api_get_sim_location(request, iccid):
    get_or_fetch_location(iccid)
    sim = SimCard.objects.filter(iccid=iccid).first()
    if not sim:
        return JsonResponse({'error': 'SIM no encontrada'}, status=404)
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
    if request.method == "POST":
        try:
            client_name = request.POST.get("client_name").strip()
            company_name = request.POST.get("company_name").strip()
            vehicle = f"{request.POST.get("brand").strip()} {request.POST.get('model').strip()} {request.POST.get('year').strip()} {request.POST.get('color').strip()}"
            buy_date = request.POST.get("buy_date").strip()
            status = request.POST.get("status").strip()

            label = "-".join(part for part in [client_name, company_name, vehicle, buy_date] if part).strip()
            
            update_sim_label(iccid, label, status)

            sim = SimCard.objects.get(iccid=iccid)
            client = SIMAssignation.objects.filter(iccid=sim).first()

            brand = request.POST.get('brand').strip()
            model = request.POST.get('model').strip()
            year = request.POST.get('year').strip() or 0
            color = request.POST.get('color').strip()
            unit_number = request.POST.get('unit_number').strip()
            vehicle, _ = Vehicle.objects.update_or_create(
                sim = sim,
                defaults= {
                    'brand': brand,
                    'model': model,
                    'year': year,
                    'color': color,
                    'unit_number': unit_number,
                    'usuario': client.assigned_to_usuario_final if client else None,
                    'imei_gps': sim.imei,
                }
            )
            log_user_action(request.user, 'Vehicle', 'CREATE', object_id=None,
                                description=f'{request.user} registró un vehiculo')

            sim.label = label
            sim.status = status
            log_user_action(request.user, 'SimCard', 'UPDATE', object_id=sim.id,
                            description=f'{request.user} actualizó la etiqueta de la SIM: {iccid} a ("{label}")')
            sim.save()
            
            SIMAssignation.objects.update_or_create(
                iccid = sim,
                defaults = {
                    'assigned_to_usuario_final': client.assigned_to_usuario_final if client else None,
                    'assigned_to_vehicle': vehicle,
                }
            )

            return redirect("sim_details", iccid)
        except Exception as e:
            print(e)
            return redirect('get_sims')
    else:
        return redirect("sim_details", iccid)

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def send_sms(request, iccid):
    if request.method == 'POST':
        try:
            source = request.POST.get('source').strip()
            commands = request.POST.get('command')
            command_list = [line.strip() for line in commands.strip().split('\n') if line.strip()]
            
            for command in command_list:
                send_sms_api(iccid, source, command)
                log_user_action(request.user, 'SMSMessage', 'SEND_SMS', description=f'{request.user} envió un mensaje a: {iccid}')

            return redirect("sim_details", iccid)
        except Exception as e:
            print(e)
            return redirect('get_sims')
    else:
        redirect('sim_details', iccid)

@login_required
@user_in('DISTRIBUIDOR', 'REVENDEDOR')
def user_details(request, type, id):
    user = request.user
    lang, base = LANG_USER.get(user.preferred_lang, LANG_USER['es'])
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

    if type.upper() not in model_map:
        raise Http404()

    ModelClass = model_map[type.upper()]
    
    if user_type == 'MATRIZ':
        details = get_object_or_404(ModelClass, id=id)

        if type == 'DISTRIBUIDOR':
            linked_revendedor = Revendedor.objects.filter(distribuidor=details)
            linked_final = Cliente.objects.filter(Q(distribuidor=details) | Q(revendedor__distribuidor=details))
            linked_sims = get_assigned_sims(details.user, with_label=True)

        elif type == 'REVENDEDOR':
            linked_final = Cliente.objects.filter(revendedor=details)
            linked_sims = get_assigned_sims(details.user, with_label=True)

        elif type == 'CLIENTE':
            linked_sims = get_assigned_sims(details.user, with_label=True)
            linked_vehicles = [vehicle.get_vehicle() for vehicle in Vehicle.objects.filter(cliente_id=details)]

    elif user_type == 'DISTRIBUIDOR':
        distribuidor = Distribuidor.objects.get(user=user)

        if type == 'REVENDEDOR':
            details = get_object_or_404(Revendedor, id=id, distribuidor=distribuidor)
            linked_final = Cliente.objects.filter(revendedor=details)
            linked_sims = get_assigned_sims(details.user, with_label=True)

        elif type == 'CLIENTE':
            details = get_object_or_404(Cliente, Q(distribuidor=distribuidor) | Q(revendedor__distribuidor=distribuidor), id=id)
            linked_sims = get_assigned_sims(details.user, with_label=True)
            linked_vehicles = [vehicle.get_vehicle() for vehicle in Vehicle.objects.filter(cliente_id=details)]

        else:
            raise Http404()

    elif user_type == 'REVENDEDOR':
        revendedor = Revendedor.objects.get(user=user)

        if type == 'CLIENTE':
            details = get_object_or_404(Cliente, revendedor=revendedor, id=id)
            linked_sims = get_assigned_sims(details.user, with_label=True)
            linked_vehicles = [vehicle.get_vehicle() for vehicle in Vehicle.objects.filter(cliente_id=details)]
        else:
            raise Http404()
    else:
        raise Http404()

    mid_sim = len(linked_sims)//2 if linked_sims else 0
    mid_veh = len(linked_vehicles)//2 if linked_vehicles else 0
    is_active = User.objects.get(id=details.user_id).is_active

    return render(request, 'user_details.html', {
        'user': details,
        'type': type.lower(),
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
                log_user_action(request.user, 'User', 'DISABLE' if user.is_active else 'ENABLE', object_id=User.id, 
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

def send_email_async(subject, message, from_email, recipient_list):
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def update_user(request, user_id):
    if request.method != 'POST':
        return redirect('get_users')
    
    user_obj = get_object_or_404(User, id=user_id)
    user_type_model_map = {
        'DISTRIBUIDOR': Distribuidor,
        'REVENDEDOR': Revendedor,
        'FINAL': Cliente,
    }

    model = user_type_model_map.get(user_obj.user_type)
    if not model:
        return Http404()
    
    related_obj = model.objects.get(user=user_obj)
    first_name = request.POST.get("first_name").strip()
    last_name = request.POST.get("last_name").strip()
    email = request.POST.get("email").strip().lower()
    phone = request.POST.get("phone_number").strip()
    rfc = request.POST.get('rfc').strip()

    if User.objects.filter(email=email).exclude(id=user_id).exists():
        messages.error(request, "El correo ya está registrado.")
        return redirect('user_details', type=user_obj.user_type, id=related_obj.id)

    user_obj.username = email
    user_obj.first_name = first_name
    user_obj.last_name = last_name
    user_obj.email = email
    
    base = first_name[:2].upper() + last_name[:2].lower() + phone[-4:]
    password = f"{base}!{rfc[-2:]}" if rfc else base

    user_obj.set_password(password)
    user_obj.save()

    threading.Thread(
        target=send_email_async,
        args=(
            'Nueva contraseña',
            f"""
            Hola {first_name},
            Se ha actualizado tu contraseña de la plataforma 1iox.
            Usuario: {user_obj.username}
            Tu nueva contraseña es:
            👉 {password}

            Saludos,
            El equipo de 1iox
            """,
            SENDER_EMAIL,
            [email]
        )
    ).start()

    threading.Thread(
        target=send_email_async,
        args=(
            'Cambio de contraseña en un usuario',
            f"""
            Se ha actualizado la información y contraseña de un usuario
            La información de inicio de sesión de {first_name} {last_name} ({user_obj.user_type}) es:
            Usuario: {user_obj.username}
            Contraseña: {password}

            Saludos,    
            El equipo de administración.
            """,
            SENDER_EMAIL,
            [SENDER_EMAIL]
        )
    ).start()

    fields_to_update = [
        'first_name', 'last_name', 'email', 'phone_number', 'company', 'rfc', 'street', 
        'city', 'zip', 'state', 'country'
    ]

    for field in fields_to_update:
        if hasattr(related_obj, field):
            setattr(related_obj, field, request.POST.get(field, getattr(related_obj, field)))

    log_user_action(request.user, model.__name__, 'UPDATE', object_id=user_obj.id, description=f'{request.user} actualizó los datos de {user_obj}')
    related_obj.save()

    return redirect('user_details', user_obj.user_type, related_obj.id)
