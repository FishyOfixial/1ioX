from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from ..decorators import user_in
from ..utils import get_limits, log_user_action
from .translations import es, en, pt
from ..models import GlobalLimits
from ..api_client import create_global_limits
from django.contrib import messages

LANG_MAP = {
    'es': (es.configuration, es.base),
    'en': (en.configuration, en.base),
    'pt': (pt.configuration, pt.base),
}

@login_required 
@user_in("DISTRIBUIDOR", "REVENDEDOR", 'CLIENTE')
def config(request):
    lang, base = LANG_MAP.get(request.user.preferred_lang, LANG_MAP['es'])

    data_lm, mt_lm, mo_lm = get_limits()
    data_opt = [
        (9, '10 MB'),
        (10, '20 MB'),
        (17, '30 MB'),
        (16, '40 MB'),
    ]
    mt_opt = [
        (45, '10 SMS'),
        (29, '25 SMS'),
        (28, '50 SMS'),
        (5, '100 SMS')
    ]
    mo_opt = [
        (35, '10 SMS'),
        (31, '25 SMS'),
        (30, '50 SMS'),
        (7, '100 SMS')
    ]

    context = {
        'options': {
            'data': data_opt,
            'mt': mt_opt,
            'mo': mo_opt
        },
        'limits': {
            'data': data_lm,
            'mt': mt_lm,
            'mo': mo_lm,
        },
        'lang': lang,
        'base': base,
    }
    return render(request, 'configuration.html', context)

def update_limits(request):
    if request.method == "POST":
        try:
            data = request.POST.get('data-select')
            mt = request.POST.get('mt-select')
            mo = request.POST.get('mo-select')
            create_global_limits(data, mt, mo)

            limits = GlobalLimits.objects.first()
            limits.data_limit = data
            limits.mt_limit = mt
            limits.mo_limit = mo
            limits.save()

            log_user_action(request.user, 'GlobalLimits', 'UPDATE', object_id=None, description=f'{request.user} actualizó los limites globales')
            messages.success(request, "Cambios guardados correctamente.")

            return redirect("configuration")
        except Exception as e:
            messages.error(request, 'Error guardando los cambios.')
            return redirect('configuration')
    else:
        return redirect("configuration")