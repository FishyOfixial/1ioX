from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.liv_, name="login"),
    path('logout/', views.lov_, name="logout"),

    path('', views.ds_, name='dashboard'),
    path('detalles-orden/<int:order_number>/', views.od_, name="order_details"),
    
    path('mis-sim/', views.gs_, name='get_sims'),
    path('cambiar-estado-sims/', views.uss_, name="update_sim_state"),
    path('asignar_sims/', views.as_, name="assign_sims"),
    path('cambiar-etiqueta/<int:iccid>', views.usl_, name="update_label"),
    path('mis-sim/detalles-sim/<int:iccid>/', views.sd_, name="sim_details"),
    path('mis-sim/send-sms/<int:iccid>/', views.ss_, name="send_sms"),

    path('usuarios/', views.gu_, name='get_users'),
    path('usuarios/crear-distribuidor/', views.cd_, name='create_distribuidor'),
    path('usuarios/crear-revendedor/', views.cr_, name='create_revendedor'),
    path('usuarios/crear-cliente/', views.cc_, name='create_cliente'),
    path('usuarios/detalles-<str:type>/<int:id>', views.ud_, name='user_details'),
    path('usuarios/editar-usuario/<int:user_id>', views.uu_, name='update_user'),
    path('usuarios/editar-status-usuario/<int:user_id>', views.uua_, name='update_user_account'),

    path('configuracion/', views.co_, name='configuration'),
    path('configuracion/limites-globales/', views.gl_, name='update_limits'),

    path('refresh-monthly-usage/', views.rm_, name="refresh_monthly"),
    path('refresh-orders/', views.ro_, name="refresh_orders"),
    path('refresh-sim/', views.rsim_, name="refresh_sim"),
    path('refresh-data-quota/', views.rdq_, name="refresh_data_quota"),
    path('refresh-sms-quota/', views.rsq_, name="refresh_sms_quota"),
    path('refresh-status/', views.rsta_, name="refresh_status"),
    path('refresh-sms/<int:iccid>', views.rsms_, name='refresh_sms'),

    path('usage-task/', views.cron_usage),
    path('status-task/', views.cron_status),
]
