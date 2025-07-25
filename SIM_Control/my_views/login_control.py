from django.shortcuts import render, redirect
from ..forms import CustomLoginForm
from django.contrib.auth import authenticate, login, logout
from ..utils import log_user_action

def login_view(request):
    if request.method == 'GET':
        return render(request, 'login.html', {'form': CustomLoginForm()})
    
    user = authenticate(request,
                        username=request.POST['username'].strip(),
                        password=request.POST['password'].strip())
    
    if user is None:
        return render(request, 'login.html', {'error': 'Correo o contraseña inválido', 'form': CustomLoginForm()})
    else:
        login(request, user)
        log_user_action(user, 'User', 'LOGIN', description=f'{request.user} inicio sesión')
        return redirect('dashboard')

def logout_view(request):
    log_user_action(request.user, 'User', 'LOGOUT', description=f'{request.user} cerró sesión')
    logout(request)
    return redirect('login')
