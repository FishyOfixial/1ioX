from django.urls import path

from customer_portal import views

app_name = "customer_portal"

urlpatterns = [
    path("", views.customer_dashboard, name="dashboard"),
    path("sim/<int:sim_id>/", views.customer_sim_detail, name="sim_detail"),
]