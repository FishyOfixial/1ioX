from django.shortcuts import render, redirect, get_object_or_404
from .api_client import *
from .models import *
from .utils import get_data_monthly_usage, get_top_data_usage_per_month, get_top_sms_usage_per_month
from .decorators import user_is, user_in
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import CustomLoginForm, DistribuidorForm, RevendedorForm, ClienteForm
import json
from django.http import JsonResponse, HttpResponseForbidden, Http404
from django.core.management import call_command
from django.db.models import Count, Q

def is_matriz(user):
    return user.is_authenticated and user.user_type == 'MATRIZ'

def get_assigned_iccids(user):
    if user.user_type == 'MATRIZ':
        return None
    elif user.user_type == 'DISTRIBUIDOR':
        distribuidor = Distribuidor.objects.get(user=user)
        return SIMAssignation.objects.filter(assigned_to_distribuidor=distribuidor).values_list('iccid', flat=True)
    elif user.user_type == 'REVENDEDOR':
        revendedor = Revendedor.objects.get(user=user)
        return SIMAssignation.objects.filter(assigned_to_revendedor=revendedor).values_list('iccid', flat=True)
    elif user.user_type == 'FINAL':
        usuario_final = UsuarioFinal.objects.get(user=user)
        return SIMAssignation.objects.filter(assigned_to_usuario_final=usuario_final).values_list('iccid', flat=True)
    else:
        return []

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

    all_orders = []
    all_sims = []
    all_commands = CommandRunLog.objects.all()
    monthly_usage_command = all_commands.filter(command_name="monthly_usage").first()
    update_orders_command = all_commands.filter(command_name="update_orders").first()
    update_sims_command = all_commands.filter(command_name="update_sims").first()

    assigned_sims = get_assigned_iccids(user)
    if user.user_type == 'MATRIZ':
        all_sims = SimCard.objects.all()
        all_orders = Order.objects.all()

    elif user.user_type == 'DISTRIBUIDOR':
        all_sims = SimCard.objects.filter(iccid__in=assigned_sims)

    elif user.user_type == 'REVENDEDOR':
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


    return render(request, 'dashboard.html', {
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
            'all_orders': all_orders,
        },
    })

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

    return render(request, 'order_details.html', {
        'order': order,
        'order_sims': order_sims,
        'total_sims': total_sims,
        'shipping_address': shipping_address,
        'order_one': order_one,
        'order_two': order_two
    })

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def get_sims(request):
    user = request.user
    assigned_iccids = get_assigned_iccids(user)

    if assigned_iccids is None:
        sims_qs = SimCard.objects.all()
    else:
        sims_qs = SimCard.objects.filter(iccid__in=assigned_iccids)

    sims_dict = {sim.iccid: sim for sim in sims_qs}
    quotas_dict = {q.iccid: q for q in SIMQuota.objects.filter(iccid__in=sims_dict.keys())}
    status_dict = {s.iccid: s for s in SIMStatus.objects.filter(iccid__in=sims_dict.keys())}

    rows = []
    for iccid in sims_dict.keys():
        sim = sims_dict[iccid]
        quota = quotas_dict.get(iccid)
        stat = status_dict.get(iccid)

        rows.append({
            'iccid': iccid,
            'isEnable': sim.status,
            'imei': sim.imei,
            'label': sim.label,
            'status': stat.status if stat else "UNKNOWN",
            'volume': quota.volume if quota else 0,
        })

    return render(request, 'get_sims.html', {
            'rows': rows,
        })

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def update_sim_state(request):
    if request.method == "POST":
        try:
            status = request.POST.get("status", "Enabled")
            iccids = json.loads(request.POST.get("iccids", "[]"))
            labels = json.loads(request.POST.get("labels", "[]"))

            update_sims_status(iccids, labels, status)

            return redirect("get_sims")
        except Exception as e:
            return render(request, "error.html", {"error": str(e)})
    else:
        return redirect("get_sims")

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def refresh_sim_table(request):
    try:
        call_command('update_sims')
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def refresh_monthly(resquest):
    try:
        call_command('monthly_usage')
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

# Activa la asignacion cuando ya quede al menos un usuario Iván, que no se te olvide
@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def sim_details(request, iccid):
    user = request.user

    assigned_sims = get_assigned_iccids(user)
    if assigned_sims is not None and str(iccid) not in assigned_sims:
        return HttpResponseForbidden("No tienes permiso para ver esta SIM.")

    sim = get_object_or_404(SimCard, iccid=iccid)
    assignation = SIMAssignation.objects.filter(iccid=iccid).first()
    data_quota = SIMQuota.objects.get(iccid=iccid)
    sms_quota = SIMSMSQuota.objects.get(iccid=iccid)
    status = SIMStatus.objects.get(iccid=iccid)
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

    monthly_usage_command = all_commands.get(command_name='monthly_usage')
    data_quota_command = all_commands.get(command_name='update_data_quotas')
    sms_quota_command = all_commands.get(command_name='update_sms_quotas')

    return render(request, 'sim_details.html', {
        'sim': sim,
        'assignation': assignation,
        'data_quota': data_quota,
        'sms_quota': sms_quota,
        'status': status,
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
        }
    })


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

    return render(request, 'get_users.html', {
        'all_distribuidor': all_distribuidor,
        'all_revendedor': all_revendedor,
        'all_clientes': all_clientes,
    })

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
        distribuidor_id = 0
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
def user_details(request, type, id):
    linked_revendedor = []
    linked_final = []
    linked_sims = []
    user = request.user

    if user.user_type == 'MATRIZ':

        if type == 'DISTRIBUIDOR':
            details = get_object_or_404(Distribuidor, id=id)
            linked_revendedor = Revendedor.objects.filter(distribuidor=details)
            linked_final = UsuarioFinal.objects.filter(Q(distribuidor=details) | Q(revendedor__distribuidor=details))
            linked_sims = get_assigned_iccids(details.user)

        elif type == 'REVENDEDOR':
            details = get_object_or_404(Revendedor, id=id)
            linked_final = UsuarioFinal.objects.filter(revendedor=details)
            linked_sims = get_assigned_iccids(details.user)
        elif type == 'FINAL':
            details = get_object_or_404(UsuarioFinal, id=id)
            linked_sims = get_assigned_iccids(details.user)

        else:
            raise Http404()
        
        mid = len(linked_sims)//2

        return render(request,'user_details.html', {
            'user': details,
            'type': type.lower(),
            'linked_revendedor': linked_revendedor,
            'linked_final': linked_final,
            'linked_sims_one': linked_sims[:mid],
            'linked_sims_two': linked_sims[mid:],
            'total_sims': linked_sims.count()
        })
    
    if user.user_type == 'DISTRIBUIDOR':
        distribuidor = Distribuidor.objects.get(user=user)

        if type == 'REVENDEDOR':
            details = get_object_or_404(Revendedor, id=id, distribuidor=distribuidor)
            linked_final = UsuarioFinal.objects.filter(revendedor=details)
            linked_sims = get_assigned_iccids(details.user)
        elif type == 'FINAL':
            details = get_object_or_404(UsuarioFinal, Q(distribuidor=distribuidor) | Q(revendedor__distribuidor=distribuidor),id=id)
            linked_sims = get_assigned_iccids(details.user)
        elif type == 'DISTRIBUIDOR':
            raise Http404()
        else:
            raise Http404()
        if not details:
            raise Http404()
        
        mid = len(linked_sims)//2

        return render(request,'user_details.html', {
            'user': details,
            'type': type.lower(),
            'linked_final': linked_final,
            'linked_sims_one': linked_sims[:mid],
            'linked_sims_two': linked_sims[mid:],
            'total_sims': linked_sims.count()
        })
    
    if user.user_type == 'REVENDEDOR':
        revendedor = Revendedor.objects.get(user=user)

        if type == 'FINAL':
            details = get_object_or_404(UsuarioFinal, revendedor=revendedor, id=id)
            linked_sims = get_assigned_iccids(details.user)
        elif type in ['DISTRIBUIDOR', 'REVENDEDOR']:
            raise Http404()
        else:
            raise Http404()
        if not details:
            raise Http404()
        
        mid = len(linked_sims)//2

        return render(request,'user_details.html', {
            'user': details,
            'type': type.lower(),
            'linked_final': linked_final,
            'linked_sims_one': linked_sims[:mid],
            'linked_sims_two': linked_sims[mid:],
            'total_sims': linked_sims.count()
        })
    
    raise Http404()

@login_required
def update_user(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        user_obj.username = request.POST.get('email')
        user_obj.first_name = request.POST.get('first_name')
        user_obj.last_name = request.POST.get('last_name')
        user_obj.email = request.POST.get('email')
        user_obj.save()

        if user_obj.user_type == 'DISTRIBUIDOR':
            distribuidor = Distribuidor.objects.get(user=user_obj)
            distribuidor.first_name = request.POST.get('first_name')
            distribuidor.last_name = request.POST.get('last_name')
            distribuidor.email = request.POST.get('email')
            distribuidor.phone_number = request.POST.get('phone_number')
            distribuidor.company = request.POST.get('company')
            distribuidor.rfc = request.POST.get('rfc')
            distribuidor.street = request.POST.get('street')
            distribuidor.city = request.POST.get('city')
            distribuidor.zip = request.POST.get('zip')
            distribuidor.state = request.POST.get('state')
            distribuidor.country = request.POST.get('country')
            distribuidor.save()

        if user_obj.user_type == 'REVENDEDOR':
            revendedor = Revendedor.objects.get(user=user_obj)
            revendedor.first_name = request.POST.get('first_name')
            revendedor.last_name = request.POST.get('last_name')
            revendedor.email = request.POST.get('email')
            revendedor.phone_number = request.POST.get('phone_number')
            revendedor.company = request.POST.get('company')
            revendedor.rfc = request.POST.get('rfc')
            revendedor.street = request.POST.get('street')
            revendedor.city = request.POST.get('city')
            revendedor.zip = request.POST.get('zip')
            revendedor.state = request.POST.get('state')
            revendedor.country = request.POST.get('country')
            revendedor.save()

        if user_obj.user_type == 'FINAL':
            cliente = UsuarioFinal.objects.get(user=user_obj)
            cliente.first_name = request.POST.get('first_name')
            cliente.last_name = request.POST.get('last_name')
            cliente .email = request.POST.get('email')
            cliente.phone_number = request.POST.get('phone_number')
            cliente.company = request.POST.get('company')
            cliente.street = request.POST.get('street')
            cliente.city = request.POST.get('city')
            cliente.zip = request.POST.get('zip')
            cliente.state = request.POST.get('state')
            cliente.country = request.POST.get('country')
            cliente.save()

        return redirect('get_users')
