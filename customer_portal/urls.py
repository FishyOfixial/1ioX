from django.urls import path

from customer_portal import views

app_name = "customer_portal"

urlpatterns = [
    path("", views.customer_dashboard, name="dashboard"),
    path("sim/<int:sim_id>/", views.customer_sim_detail, name="sim_detail"),
    path("sim/<int:sim_id>/checkout/", views.customer_create_checkout, name="create_checkout"),
    path("payments/success/", views.payment_success, name="payment_success"),
    path("payments/pending/", views.payment_pending, name="payment_pending"),
    path("payments/failure/", views.payment_failure, name="payment_failure"),
    path("payments/webhook/", views.payment_webhook, name="payment_webhook"),
]
