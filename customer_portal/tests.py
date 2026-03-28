import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.urls import reverse

from auditlogs.models import SystemLog
from billing.models import MembershipPlan
from SIM_Control.models import Cliente, SIMAssignation, SimCard, User


class CustomerPortalSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="cliente@example.com",
            email="cliente@example.com",
            password="testpass123",
            user_type="CLIENTE",
        )
        self.cliente = Cliente.objects.create(
            user=self.user,
            first_name="Cliente",
            last_name="Seguro",
            email=self.user.email,
            phone_number="+52 5550001111",
            company="Cliente Seguro",
            street="Street",
            city="City",
            state="State",
            zip="12345",
            country="MX",
        )
        self.sim = SimCard.objects.create(iccid="8901000000000099991", status="Disabled")
        cliente_ct = ContentType.objects.get_for_model(Cliente)
        SIMAssignation.objects.create(sim=self.sim, content_type=cliente_ct, object_id=self.cliente.id)
        self.plan = MembershipPlan.objects.create(
            name="Plan Cliente",
            duration_days=30,
            period_unit="day",
            period_count=30,
            price=Decimal("200.00"),
            is_active=True,
        )
        self.client.force_login(self.user)

    @override_settings(PUBLIC_BASE_URL="https://panel.1iox.com")
    @patch("customer_portal.views.create_checkout_for_plan", return_value="https://checkout.example.com")
    def test_checkout_uses_public_base_url(self, create_checkout_mock):
        response = self.client.post(
            reverse("customer_portal:create_checkout", args=[self.sim.id]),
            {"plan_id": self.plan.id},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://checkout.example.com")
        create_checkout_mock.assert_called_once()
        self.assertEqual(create_checkout_mock.call_args.kwargs["base_url"], "https://panel.1iox.com")
        self.assertEqual(
            create_checkout_mock.call_args.kwargs["notification_url"],
            "https://panel.1iox.com/billing/mercadopago/notification/",
        )

    @override_settings(MERCADOPAGO_WEBHOOK_TOKEN="secret-token")
    @patch("customer_portal.views.process_mercadopago_payment", return_value=True)
    def test_webhook_log_is_sanitized(self, process_payment_mock):
        payload = {
            "type": "payment",
            "action": "payment.created",
            "live_mode": True,
            "user_id": "123",
            "data": {"id": "payment-1"},
            "sensitive": {"card": "4111111111111111"},
        }

        response = self.client.post(
            reverse("mercadopago_webhook_root"),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_WEBHOOK_TOKEN="secret-token",
        )

        self.assertEqual(response.status_code, 200)
        process_payment_mock.assert_called_once_with("payment-1")
        webhook_log = SystemLog.objects.filter(message="Webhook received").first()
        self.assertIsNotNone(webhook_log)
        self.assertNotIn("payload", webhook_log.metadata)
        self.assertEqual(webhook_log.metadata["event_type"], "payment")
        self.assertEqual(webhook_log.metadata["payment_id"], "payment-1")
