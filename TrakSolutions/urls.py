from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('portal/', include(('customer_portal.urls', 'customer_portal'), namespace='customer_portal')),
    path('', include(('billing.urls', 'billing'), namespace='billing')),
    path('', include('SIM_Control.urls')),
]

handler404 = 'SIM_Control.views.role_based_404_redirect'
