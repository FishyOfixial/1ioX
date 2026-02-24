from django.contrib import admin
from django.urls import path, include
from customer_portal.views import payment_webhook

urlpatterns = [
    path('admin/', admin.site.urls),
    path('billing/mercadopago/notification/', payment_webhook, name='mercadopago_webhook_root'),
    path('billing/mercadopago/notification', payment_webhook),
    path('portal/', include(('customer_portal.urls', 'customer_portal'), namespace='customer_portal')),
    path('', include(('billing.urls', 'billing'), namespace='billing')),
    path('', include('SIM_Control.urls')),
]

handler404 = 'SIM_Control.views.role_based_404_redirect'
