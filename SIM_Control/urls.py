from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name="login"),
    path('logout/', views.logout_view, name="logout"),

    path('', views.dashboard, name='dashboard'),
    path('refresh-monthly-usage/', views.refres_monthly, name="refresh_monthly"),
    path('detalles-orden/<int:order_number>/', views.order_details, name="order_details"),
    
    path('mis-sim/', views.get_sims, name='get_sims'),
    path('cambiar-estado-sims/', views.update_sim_state, name="update_sim_state"),
    path('refresh-sim-table/', views.refresh_sim_table, name="refresh_sim_table"),
    path('mis-sim/detalles-sim/<int:iccid>/', views.sim_details, name="sim_details"),
    

    path('usuarios/', views.get_users, name='get_users'),
    path('usuarios/crear-distribuidor/', views.create_distribuidor, name='create_distribuidor'),
    path('usuarios/crear-revendedor/', views.create_revendedor, name='create_revendedor'),
    path('usuarios/crear-cliente/', views.create_cliente, name='create_cliente'),
    path('usuarios/detalles-<str:type>/<int:id>', views.user_details, name='user_details'),
    path('usuarios/editar-usuario/<int:user_id>', views.update_user, name='update_user'),

]
