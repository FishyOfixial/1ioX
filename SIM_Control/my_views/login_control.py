from django.shortcuts import render, redirect
from ..forms import CustomLoginForm
from django.contrib.auth import authenticate, login, logout
from ..utils import log_user_action

def login_view(request):
    if request.method == 'GET':
        return render(request, 'login.html', {'form': CustomLoginForm()})
    
    user = authenticate(request,
                        username=(request.POST.get('username') or '').strip(),
                        password=(request.POST.get('password') or '').strip())
    
    if user is None:
        return render(request, 'login.html', {'error': 'Correo o contraseña inválido', 'form': CustomLoginForm()})
    else:
        login(request, user)
        log_user_action(user, 'User', 'LOGIN', description=f'{user} inicio sesión')
        return redirect('configuration' if user.user_type == 'CLIENTE' else 'dashboard')

def logout_view(request):
    log_user_action(request.user, 'User', 'LOGOUT', description=f'{request.user} cerró sesión')
    logout(request)
    return redirect('login')


