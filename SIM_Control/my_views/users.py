from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from ..decorators import user_in, matriz_required
from ..models import Distribuidor, Revendedor, Cliente, SIMAssignation
from django.db.models import Count
from ..utils import log_user_action
from ..forms import DistribuidorForm, RevendedorForm, ClienteForm
from django.shortcuts import redirect, render
from .translations import get_translation

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def get_users(request):
    user = request.user

    lang, base = get_translation(user, "users")
    all_distribuidor = []
    all_revendedor = []
    all_clientes = []

    distribuidor_ct = ContentType.objects.get_for_model(Distribuidor)
    revendedor_ct = ContentType.objects.get_for_model(Revendedor)
    cliente_ct = ContentType.objects.get_for_model(Cliente)

    def attach_counts(items, ct):
        ids = [obj.id for obj in items]
        if not ids:
            return
        counts = {
            row['object_id']: row['c']
            for row in SIMAssignation.objects.filter(content_type=ct, object_id__in=ids)
            .values('object_id')
            .annotate(c=Count('id'))
        }
        for obj in items:
            obj.sim_count = counts.get(obj.id, 0)

    if user.user_type == 'MATRIZ':
        all_distribuidor = Distribuidor.objects.select_related("user").only(
            "id", "first_name", "last_name", "company", "user_id"
        )
        all_revendedor = Revendedor.objects.select_related("user", "distribuidor").only(
            "id", "first_name", "last_name", "company", "user_id", "distribuidor_id"
        )
        all_clientes = Cliente.objects.select_related("user", "distribuidor", "revendedor").only(
            "id", "first_name", "last_name", "company", "user_id", "distribuidor_id", "revendedor_id"
        )
        attach_counts(all_distribuidor, distribuidor_ct)
        attach_counts(all_revendedor, revendedor_ct)
        attach_counts(all_clientes, cliente_ct)
    
    elif user.user_type == 'DISTRIBUIDOR':
        distribuidor_obj = Distribuidor.objects.get(user=user)
        all_revendedor = Revendedor.objects.filter(distribuidor_id=distribuidor_obj).select_related("user").only(
            "id", "first_name", "last_name", "company", "user_id", "distribuidor_id"
        )
        all_clientes = Cliente.objects.filter(distribuidor_id=distribuidor_obj).select_related("user").only(
            "id", "first_name", "last_name", "company", "user_id", "distribuidor_id", "revendedor_id"
        )
        attach_counts(all_revendedor, revendedor_ct)
        attach_counts(all_clientes, cliente_ct)
    
    elif user.user_type == 'REVENDEDOR':
        revendedor_obj = Revendedor.objects.get(user=user)
        all_clientes = Cliente.objects.filter(revendedor_id=revendedor_obj).select_related("user").only(
            "id", "first_name", "last_name", "company", "user_id", "distribuidor_id", "revendedor_id"
        )
        attach_counts(all_clientes, cliente_ct)
    
    context = {
        'lang': lang,
        'base': base,
        'all_distribuidor': all_distribuidor,
        'all_revendedor': all_revendedor,
        'all_clientes': all_clientes,
        }

    return render(request, 'get_users.html', context)

@matriz_required
def create_distribuidor(request):
    lang, base = get_translation(request.user, "register_form")
    if request.method == 'POST':
        form = DistribuidorForm(request.POST, lang=lang)
        if form.is_valid():
            form.save()
            log_user_action(request.user, 'Distribuidor', 'CREATE', object_id=None, description=f'{request.user} registro a un distribuidor')
            return redirect('get_users')
    else:
        form = DistribuidorForm(lang=lang)
    
    return render(request, 'forms/create_user.html', {'form': form, 'lang': lang, 'base': base})

@login_required
@user_in('DISTRIBUIDOR')
def create_revendedor(request):
    lang, base = get_translation(request.user, "register_form")
    user = request.user
    if user.user_type == 'MATRIZ':
        distribuidor_id = None
    elif user.user_type == 'DISTRIBUIDOR':
        distribuidor_id = Distribuidor.objects.get(user=user).id

    if request.method == 'POST':
        form = RevendedorForm(request.POST, lang=lang)

        if form.is_valid():
            log_user_action(request.user, 'Revendedor', 'CREATE', object_id=None, description=f'{request.user} registro a un revendedor')
            form.save(distribuidor_id=distribuidor_id)
            return redirect('get_users')
    else:
        form = RevendedorForm(lang=lang)
    
    return render(request, 'forms/create_user.html', {'form': form, 'lang': lang, 'base': base})

@login_required
@user_in('DISTRIBUIDOR', 'REVENDEDOR')
def create_cliente(request):
    user = request.user
    lang, base = get_translation(request.user, "register_form")
    if user.user_type == 'MATRIZ':
        distribuidor_id = None
        revendedor_id = None
    elif user.user_type == 'DISTRIBUIDOR':
        distribuidor_id = Distribuidor.objects.get(user=user).id
        revendedor_id = None
    elif user.user_type == 'REVENDEDOR':
        revendedor_obj = Revendedor.objects.get(user=user)
        distribuidor_id = revendedor_obj.distribuidor_id
        revendedor_id = revendedor_obj.id

    if request.method == 'POST':
        form = ClienteForm(request.POST, lang=lang)

        if form.is_valid():
            log_user_action(request.user, 'Cliente', 'CREATE', object_id=None, description=f'{request.user} registro a un cliente')
            form.save(distribuidor_id=distribuidor_id, revendedor_id=revendedor_id)
            return redirect('get_users')
    else:
        form = ClienteForm(lang=lang)
    
    return render(request, 'forms/create_user.html', {'form': form, 'lang': lang, 'base': base})
