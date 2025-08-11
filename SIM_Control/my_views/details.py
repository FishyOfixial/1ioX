from ..decorators import user_in
from django.contrib.auth.decorators import login_required, user_passes_test
from ..utils import is_matriz, get_assigned_iccids, get_or_fetch_sms, get_or_fetch_location, log_user_action
from ..models import *
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponseForbidden, Http404
from django.db.models import Q
from ..api_client import update_sim_label, send_sms_api
from operator import attrgetter
from .translations import en, es, pt

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
    assigned_sims = get_assigned_iccids(user)
    sim = get_object_or_404(SimCard, iccid=iccid)
    if not sim:
        return Http404()
    if str(iccid) not in assigned_sims:
        return HttpResponseForbidden("No tienes permiso para ver esta SIM.")
    
    assignation = SIMAssignation.objects.filter(iccid=sim).first()
    vehicle = assignation.assigned_to_vehicle if  assignation else None
    client = assignation.assigned_to_usuario_final if assignation else None
    data_quota = SIMQuota.objects.filter(iccid=iccid).first()
    sms_quota = SIMSMSQuota.objects.filter(iccid=iccid).first()
    status = SIMStatus.objects.filter(iccid=iccid).first()
    monthly_usage = MonthlySimUsage.objects.filter(iccid=iccid).order_by('-month')[:6]
    monthly_usage = sorted(monthly_usage, key=attrgetter('month'))
    all_commands = CommandRunLog.objects.all()

    data_volume = data_quota.volume
    data_used = data_quota.total_volume - data_volume
    sms_volume = sms_quota.volume
    sms_used = sms_quota.total_volume - sms_volume
    monthly_use = [
        {
            'month': month.month,
            'data_used': month.data_volume,
            'sms_used': month.sms_volume
        }
        for month in monthly_usage
    ]
    monthly_usage_command = all_commands.get(command_name='actual_usage')
    data_quota_command = all_commands.get(command_name='update_data_quotas')
    sms_quota_command = all_commands.get(command_name='update_sms_quotas')
    sms_list = get_or_fetch_sms(iccid)
    location = get_or_fetch_location(iccid)

    context = {
        'sim': sim,
        'assignation': assignation,
        'data_quota': data_quota,
        'sms_quota': sms_quota,
        'status': status,
        'sms_list': sms_list,
        'all_comands': {
            'monthly_usage': monthly_usage_command,
            'data_quota': data_quota_command,
            'sms_quota': sms_quota_command
        },
        'chart_data': {
            'data_volume': data_volume,
            'data_used': data_used,
            'sms_volume': sms_volume,
            'sms_used': sms_used,
            'monthly_use': monthly_use,
        },
        'location': location,
        'vehicle': vehicle,
        'client':  client,
        'lang': lang,
        'base': base
    }
        
    return render(request, 'sim_details.html', context)

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
        'FINAL': UsuarioFinal
    }

    if type.upper() not in model_map:
        raise Http404()

    ModelClass = model_map[type.upper()]
    
    if user_type == 'MATRIZ':
        details = get_object_or_404(ModelClass, id=id)

        if type == 'DISTRIBUIDOR':
            linked_revendedor = Revendedor.objects.filter(distribuidor=details)
            linked_final = UsuarioFinal.objects.filter(Q(distribuidor=details) | Q(revendedor__distribuidor=details))
            linked_sims = get_assigned_iccids(details.user, with_label=True)

        elif type == 'REVENDEDOR':
            linked_final = UsuarioFinal.objects.filter(revendedor=details)
            linked_sims = get_assigned_iccids(details.user, with_label=True)

        elif type == 'FINAL':
            linked_sims = get_assigned_iccids(details.user, with_label=True)
            linked_vehicles = [vehicle.get_vehicle() for vehicle in Vehicle.objects.filter(usuario_id=details)]

    elif user_type == 'DISTRIBUIDOR':
        distribuidor = Distribuidor.objects.get(user=user)

        if type == 'REVENDEDOR':
            details = get_object_or_404(Revendedor, id=id, distribuidor=distribuidor)
            linked_final = UsuarioFinal.objects.filter(revendedor=details)
            linked_sims = get_assigned_iccids(details.user, with_label=True)

        elif type == 'FINAL':
            details = get_object_or_404(UsuarioFinal, Q(distribuidor=distribuidor) | Q(revendedor__distribuidor=distribuidor), id=id)
            linked_sims = get_assigned_iccids(details.user, with_label=True)
            linked_vehicles = [vehicle.get_vehicle() for vehicle in Vehicle.objects.filter(usuario_id=details)]

        else:
            raise Http404()

    elif user_type == 'REVENDEDOR':
        revendedor = Revendedor.objects.get(user=user)

        if type == 'FINAL':
            details = get_object_or_404(UsuarioFinal, revendedor=revendedor, id=id)
            linked_sims = get_assigned_iccids(details.user, with_label=True)
            linked_vehicles = [vehicle.get_vehicle() for vehicle in Vehicle.objects.filter(usuario_id=details)]
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

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def update_user(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)

    if request.method != 'POST':
        return redirect('get_users')

    user_obj.username = request.POST.get('email')
    user_obj.first_name = request.POST.get('first_name')
    user_obj.last_name = request.POST.get('last_name')
    user_obj.email = request.POST.get('email')
    user_obj.save()

    user_type_model_map = {
        'DISTRIBUIDOR': Distribuidor,
        'REVENDEDOR': Revendedor,
        'FINAL': UsuarioFinal,
    }

    model = user_type_model_map.get(user_obj.user_type)
    if model:
        related_obj = model.objects.get(user=user_obj)

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
