from django.contrib.auth.decorators import login_required, user_passes_test
from ..decorators import user_in
from ..models import Distribuidor, Revendedor, UsuarioFinal
from django.db.models import Count
from ..utils import is_matriz, log_user_action
from ..forms import DistribuidorForm, RevendedorForm, ClienteForm
from django.shortcuts import redirect, render
from .translations import es, en, pt

LANG_MAP_USERS = {
    'es': (es.users, es.base),
    'en': (en.users, en.base),
    'pt': (pt.users, pt.base)
}

LANG_MAP_FORM = {
    'es': (es.register_form, es.base),
    'en': (en.register_form, en.base),
    'pt': (pt.register_form, pt.base)
}



@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def get_users(request):
    user = request.user

    lang, base = LANG_MAP_USERS.get(user.preferred_lang, LANG_MAP_USERS['es'])
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
        'lang': lang,
        'base': base,
        'all_distribuidor': all_distribuidor,
        'all_revendedor': all_revendedor,
        'all_clientes': all_clientes,
        }

    return render(request, 'get_users.html', context)

@login_required
@user_passes_test(is_matriz)
def create_distribuidor(request):
    lang, base = LANG_MAP_FORM.get(request.user.preferred_lang, LANG_MAP_FORM['es'])
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
    lang, base = LANG_MAP_FORM.get(request.user.preferred_lang, LANG_MAP_FORM['es'])
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
    lang, base = LANG_MAP_FORM.get(request.user.preferred_lang, LANG_MAP_FORM['es'])
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
        form = ClienteForm(request.POST, lang=lang)

        if form.is_valid():
            log_user_action(request.user, 'UsuarioFinal', 'CREATE', object_id=None, description=f'{request.user} registro a un cliente')
            form.save(distribuidor_id=distribuidor_id, revendedor_id=revendedor_id)
            return redirect('get_users')
    else:
        form = ClienteForm(lang=lang)
    
    return render(request, 'forms/create_user.html', {'form': form, 'lang': lang, 'base': base})
