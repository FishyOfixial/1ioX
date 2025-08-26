from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Case, When
from ..utils import is_matriz
from .translations import es, en, pt
from ..models import SIMAssignation, UserActionLog, User

LANG_MAP = {
    'es': (es.dashboard, es.base),
    'en': (en.dashboard, en.base),
    'pt': (pt.dashboard, pt.base)
}

@login_required
@user_passes_test(is_matriz)
def administration(request):
    user = request.user

    lang, base = LANG_MAP.get(user.preferred_lang, LANG_MAP['es'])
    logs = UserActionLog.objects.all().order_by('-timestamp')
    orden = ['MATRIZ', 'DISTRIBUIDOR', 'REVENDEDOR']
    cases = [When(user_type=value, then=pos) for pos, value in enumerate(orden)]
    users = User.objects.filter(user_type__in=orden).order_by(Case(*cases))
    
    context = {
        'base': base,
        'lang': lang,
        'filters': {
            'logs': logs,
            'users': users
        }
        
    }
    return render(request, 'admin.html', context)