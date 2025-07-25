from django.shortcuts import render, redirect, get_object_or_404
from .api_client import *
from .models import *
from .utils import get_data_monthly_usage, get_top_data_usage_per_month, get_top_sms_usage_per_month, get_or_fetch_sms, get_or_fetch_location
from .decorators import user_is, user_in, refresh_command
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import CustomLoginForm, DistribuidorForm, RevendedorForm, ClienteForm, VehicleForm
import json
from django.http import HttpResponseForbidden, Http404, JsonResponse
from django.db.models import Count, Q
from django.core.management import call_command

def is_matriz(user):
    return user.is_authenticated and user.user_type == 'MATRIZ'

def get_assigned_iccids(user, with_label=False):  
    if user.user_type == 'MATRIZ':
        sims = SimCard.objects.all()
        return sims.values('iccid', 'label') if with_label else sims.values_list('iccid', flat=True)
    model_map = {
        'DISTRIBUIDOR': Distribuidor,
        'REVENDEDOR': Revendedor,
        'FINAL': UsuarioFinal,
    }
    field_map = {
        'DISTRIBUIDOR': 'assigned_to_distribuidor',
        'REVENDEDOR': 'assigned_to_revendedor',
        'FINAL': 'assigned_to_usuario_final',
    }
    model = model_map.get(user.user_type)
    field = field_map.get(user.user_type)
    if not model or not field:
        return []
    related_obj = model.objects.get(user=user)
    filter_kwargs = {field: related_obj}

    qs = SIMAssignation.objects.filter(**filter_kwargs)

    if with_label:
        return qs.values('iccid__iccid', 'iccid__label')
    else:
        return qs.values_list('iccid__iccid', flat=True)

def get_linked_users(user):
    linked_users = []

    if user.user_type == 'DISTRIBUIDOR':
        distribuidor = Distribuidor.objects.get(user=user)

        revendedores = Revendedor.objects.filter(distribuidor=distribuidor).order_by('company')
        for rev in revendedores:
            linked_users.append({
                "user": rev.user,
                "company": rev.company,
            })

        clientes = UsuarioFinal.objects.filter(distribuidor=distribuidor).order_by('company')
        for cli in clientes:
            linked_users.append({
                "user": cli.user,
                "company": cli.company,
            })
    elif user.user_type == 'REVENDEDOR':
        revendedor = Revendedor.objects.get(user=user)

        clientes = UsuarioFinal.objects.filter(revendedor=revendedor).order_by('company')
        for cli in clientes:
            linked_users.append({
                "user": cli.user,
                "company": cli.company,
            })
    else:
        distribuidores = Distribuidor.objects.all().order_by('company')
        for dis in distribuidores:
            linked_users.append({
                "user": dis.user,
                "company": dis.company,
            })

        revendedores = Revendedor.objects.all().order_by('company')
        for rev in revendedores:
            linked_users.append({
                "user": rev.user,
                "company": rev.company,
            })

        clientes = UsuarioFinal.objects.all().order_by('company')
        for cli in clientes:
            linked_users.append({
                "user": cli.user,
                "company": cli.company,
                "user_type": "FINAL"
            })
    
    return linked_users

def login_view(request):
    if request.method == 'GET':
        return render(request, 'login.html', {'form': CustomLoginForm()})
    
    user = authenticate(request,
                        username=request.POST['username'],
                        password=request.POST['password'])
    
    if user is None:
        return render(request, 'login.html', {'error': 'Correo o contraseña inválido', 'form': CustomLoginForm()})
    else:
        login(request, user)
        return redirect('dashboard')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required 
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def dashboard(request):
    user = request.user

    all_orders = Order.objects.all
    assigned_sims = get_assigned_iccids(user)
    all_sims = SimCard.objects.filter(iccid__in=assigned_sims)
    activadas = all_sims.filter(status='Enabled').count()
    desactivadas = all_sims.filter(status='Disabled').count()
    data_suficiente = all_sims.filter(quota_status='More than 20% available').count()
    data_bajo = all_sims.filter(quota_status='Less than 20% available').count()
    data_sin_volumen = all_sims.filter(quota_status='No volume available').count()
    sms_suficiente = all_sims.filter(quota_status_SMS='More than 20% available').count()
    sms_bajo = all_sims.filter(quota_status_SMS='Less than 20% available').count()
    sms_sin_volumen = all_sims.filter(quota_status_SMS='No volume available').count()

    labels, data_usage, sms_usage = get_data_monthly_usage(assigned_sims)
    top_data_usage = get_top_data_usage_per_month(assigned_sims)
    top_sms_usage = get_top_sms_usage_per_month(assigned_sims)
    
    all_commands = CommandRunLog.objects.all()
    monthly_usage_command = all_commands.filter(command_name="actual_usage").first()
    update_orders_command = all_commands.filter(command_name="update_orders").first()
    update_sims_command = all_commands.filter(command_name="update_sims").first()

    context = {
        'activadas': activadas,
        'desactivadas': desactivadas,
        'data_suficiente': data_suficiente,
        'data_bajo': data_bajo,
        'data_sin_volumen': data_sin_volumen,
        'sms_suficiente': sms_suficiente,
        'sms_bajo': sms_bajo,
        'sms_sin_volumen': sms_sin_volumen,
        'monthly_usage': {
            'labels': labels,
            'data_usage': data_usage,
            'sms_usage': sms_usage,
            'top_data': top_data_usage,
            'top_sms': top_sms_usage,
        },
        'all_comands': {
            'monthly_usage': monthly_usage_command,
            'update_orders': update_orders_command,
            'update_sims': update_sims_command
        },
        'orders': {
            'all_orders': all_orders
        },
    }

    return render(request, 'dashboard.html', context)

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
def get_sims(request):
    user = request.user

    linked_users = get_linked_users(user)
    assigned_iccids = get_assigned_iccids(user)
    priority = {"ONLINE": 0, "ATTACHED": 1, "OFFLINE": 2, "UNKNOWN": 3}
    
    sims_qs = SimCard.objects.filter(iccid__in=assigned_iccids)
    sims_dict = {sim.iccid: sim for sim in sims_qs}
    quotas_dict = {q.iccid: q for q in SIMQuota.objects.filter(iccid__in=sims_dict.keys())}
    status_dict = {s.iccid: s for s in SIMStatus.objects.filter(iccid__in=sims_dict.keys())}

    assignations = {a.iccid.iccid: a for a in SIMAssignation.objects.filter(iccid__iccid__in=sims_dict.keys())}
    rows = []
    for iccid in sims_dict.keys():
        sim = sims_dict[iccid]
        quota = quotas_dict.get(iccid)
        stat = status_dict.get(iccid)
        assignation = assignations.get(iccid)

        rows.append({
            'iccid': iccid,
            'isEnable': sim.status,
            'imei': sim.imei,
            'label': sim.label,
            'status': stat.status if stat else "UNKNOWN",   
            'volume': quota.volume if quota else 0,
            'distribuidor': assignation.assigned_to_distribuidor.get_full_name() if assignation and assignation.assigned_to_distribuidor else '',
            'revendedor': assignation.assigned_to_revendedor.get_full_name() if assignation and assignation.assigned_to_revendedor else '',
            'cliente': assignation.assigned_to_usuario_final.get_full_name() if assignation and assignation.assigned_to_usuario_final else '',
            'whatsapp': assignation.assigned_to_usuario_final.get_phone_number() if assignation and assignation.assigned_to_usuario_final else '',
            'vehicle': assignation.assigned_to_vehicle.get_vehicle() if assignation and assignation.assigned_to_vehicle else '',
        })
    rows = sorted(rows, key=lambda r: priority.get(r["status"], 99))

    context = {
        'rows': rows,
        'linked_users': linked_users,
    }

    return render(request, 'get_sims.html', context)

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
        elif user.user_type == 'REVENDEDOR':
            sim_assign.assigned_to_distribuidor = related_obj.distribuidor

        if sim_assign not in to_create:
            to_update.append(sim_assign)

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
    user = request.user
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
                

            return redirect("get_sims")
        except Exception as e:
            return redirect('get_sims')
    else:
        return redirect("get_sims")

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def send_sms(request, iccid):
    if request.method == 'POST':
        try:
            source = request.POST.get('source')
            commands = request.POST.get('command')
            command_list = [line.strip() for line in commands.strip().split('\n') if line.strip()]
            
            for command in command_list:
                send_sms_api(iccid, source, command)

            return redirect("sim_details", iccid)
        except Exception as e:
            print(e)
            return redirect('get_sims')
    else:
        redirect('sim_details', iccid)

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def update_label(request, iccid):
    if request.method == "POST":
        try:
            client_name = request.POST.get("client_name")
            company_name = request.POST.get("company_name")
            vehicle = request.POST.get("vehicle")
            buy_date = request.POST.get("buy_date")
            status = request.POST.get("status")

            label = "-".join(part for part in [client_name, company_name, vehicle, buy_date] if part)
            
            update_sim_label(iccid, label, status)

            sim = SimCard.objects.get(iccid=iccid)
            sim.label = label
            sim.status = status
            sim.save()

            return redirect("sim_details", iccid)
        except Exception as e:
            return redirect('get_sims')
    else:
        return redirect("sim_details", iccid)

@refresh_command('update_sims')
def refresh_sim(request):
    pass

@refresh_command('actual_usage')
def refresh_monthly(request):
    pass

@refresh_command('update_orders')
def refresh_orders(request):
    pass

@refresh_command('update_status')
def refresh_status(request):
    pass

@refresh_command('update_sms_quotas')
def refresh_sms_quota(request):
    pass

@refresh_command('update_data_quotas')
def refresh_data_quota(request):
    pass

def refresh_sms(request, iccid):
    if request.method == 'POST':
        try:
            call_command('save_sms', iccid)
            return JsonResponse({"ok": True})
        except Exception as e:
            print(f"Error al ejecutar save_sms para {iccid}: {e}")
            return JsonResponse({"ok": False, "error": str(e)}, status=500)

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def sim_details(request, iccid):
    user = request.user

    assigned_sims = get_assigned_iccids(user)
    if str(iccid) not in assigned_sims:
        return HttpResponseForbidden("No tienes permiso para ver esta SIM.")
    
    sim = get_object_or_404(SimCard, iccid=iccid)
    assignation = SIMAssignation.objects.filter(iccid=sim).first()
    data_quota = SIMQuota.objects.filter(iccid=iccid).first()
    sms_quota = SIMSMSQuota.objects.filter(iccid=iccid).first()
    status = SIMStatus.objects.filter(iccid=iccid).first()
    monthly_usage = MonthlySimUsage.objects.filter(iccid=iccid)
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
        'location': location
    }
        
    return render(request, 'sim_details.html', context)

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def get_users(request):
    user = request.user

    
    all_distribuidor = []
    all_revendedor = []
    all_clientes = []

    if user.user_type == 'MATRIZ':
        all_distribuidor = Distribuidor.objects.annotate(sim_count=Count('distribuidor'))
        all_revendedor = Revendedor.objects.annotate(sim_count=Count('revendedor'))
        all_clientes = UsuarioFinal.objects.annotate(sim_count=Count('usuario_final'))
    
    elif user.user_type == 'DISTRIBUIDOR':
        distribuidor_obj = Distribuidor.objects.get(user=user)
        all_revendedor = Revendedor.objects.filter(distribuidor_id=distribuidor_obj).annotate(sim_count=Count('revendedor'))
        all_clientes = UsuarioFinal.objects.filter(distribuidor_id=distribuidor_obj).annotate(sim_count=Count('usuario_final'))
    
    elif user.user_type == 'REVENDEDOR':
        revendedor_obj = Revendedor.objects.get(user=user)
        all_clientes = UsuarioFinal.objects.filter(revendedor_id=revendedor_obj).annotate(sim_count=Count('usuario_final'))
    
    context = {
        'all_distribuidor': all_distribuidor,
        'all_revendedor': all_revendedor,
        'all_clientes': all_clientes,
        }

    return render(request, 'get_users.html', context)

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def update_user_account(request, user_id):
    if request.method == "POST":
        try:            
            action = request.POST.get("action")
            user = User.objects.get(id=user_id)

            if action == "active":
                user.is_active = not user.is_active
                user.save()
            
            elif action == "delete":
                user.delete()

            return redirect("get_users")
        except Exception as e:
            return render(request, "error.html", {"error": str(e)})
    else:
        return redirect("get_users")

@login_required
@user_passes_test(is_matriz)
def create_distribuidor(request):
    if request.method == 'POST':
        form = DistribuidorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('get_users')
    else:
        form = DistribuidorForm()
    
    return render(request, 'forms/create_distribuidor.html', {'form': form})

@login_required
@user_in('DISTRIBUIDOR')
def create_revendedor(request):
    user = request.user
    if user.user_type == 'MATRIZ':
        distribuidor_id = None
    elif user.user_type == 'DISTRIBUIDOR':
        distribuidor_id = Distribuidor.objects.get(user=user).id

    if request.method == 'POST':
        form = RevendedorForm(request.POST)

        if form.is_valid():
            form.save(distribuidor_id=distribuidor_id)
            return redirect('get_users')
    else:
        form = RevendedorForm()
    
    return render(request, 'forms/create_revendedor.html', {'form': form})

@login_required
@user_in('DISTRIBUIDOR', 'REVENDEDOR')
def create_cliente(request):
    user = request.user
    if user.user_type == 'MATRIZ':
        distribuidor_id = None
        revendedor_id = None
    elif user.user_type == 'DISTRIBUIDOR':
        distribuidor_id = Distribuidor.objects.get(user=user).id
        revendedor_id = None
    elif user.user_type == 'REVENDEDOR':
        distribuidor_id = Revendedor.objects.get(user=user).distribuidor_id
        revendedor_id = Revendedor.objects.get(user=user).id

    if request.method == 'POST':
        form = ClienteForm(request.POST)

        if form.is_valid():
            form.save(distribuidor_id=distribuidor_id, revendedor_id=revendedor_id)
            return redirect('get_users')
    else:
        form = ClienteForm()
    
    return render(request, 'forms/create_cliente.html', {'form': form})

@login_required
@user_in('DISTRIBUIDOR', 'REVENDEDOR')
def create_vehicle(request, cliente_id):
    user = request.user
    sim_cards = get_assigned_iccids(user) or SimCard.objects.all().values_list('iccid', flat=True)
    iccid_choices = [(sim, sim) for sim in sim_cards]
    if request.method == 'POST':
        form = VehicleForm(request.POST, iccid_choices=iccid_choices)
        if form.is_valid():
            sim_iccid = form.cleaned_data.get('iccid')
            form.save(cliente_id=cliente_id, sim_iccid=sim_iccid)
            return redirect('user_details', 'FINAL', cliente_id)
    else:
        form = VehicleForm(iccid_choices=iccid_choices)
    
    return render(request, 'forms/create_vehicle.html', {'form': form})

@login_required
@user_in('DISTRIBUIDOR', 'REVENDEDOR')
def user_details(request, type, id):
    user = request.user
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
        'is_active': is_active
    })

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

        related_obj.save()

    return redirect('get_users')
