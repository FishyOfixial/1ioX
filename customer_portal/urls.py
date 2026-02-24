from django.urls import path

from customer_portal import views

app_name = "customer_portal"

urlpatterns = [
    path("", views.customer_dashboard, name="dashboard"),
    path("sim/<int:sim_id>/", views.customer_sim_detail, name="sim_detail"),
    path("sim/<int:sim_id>/checkout/", views.customer_create_checkout, name="create_checkout"),
    path("checkout/bulk/preview/", views.customer_bulk_checkout_preview, name="bulk_checkout_preview"),
    path("checkout/bulk/", views.customer_bulk_checkout, name="bulk_checkout"),
    path("payments/success/", views.payment_success, name="payment_success"),
    path("payments/pending/", views.payment_pending, name="payment_pending"),
    path("payments/failure/", views.payment_failure, name="payment_failure"),
    # Production webhook URL (configured in environment): /billing/mercadopago/notification/
    path("billing/mercadopago/notification/", views.payment_webhook, name="payment_webhook"),
    path("billing/mercadopago/notification", views.payment_webhook),
    # Backward-compatible alias
    path("payments/webhook/", views.payment_webhook, name="payment_webhook_legacy"),
    path("payments/webhook", views.payment_webhook),
]
