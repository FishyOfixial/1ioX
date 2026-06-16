from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from SIM_Control.models import Cliente, Distribuidor, Revendedor, SIMAssignation, SimCard, User
from billing.models import CommissionPeriod, DistributorSale, MembershipPlan, Subscription, SubscriptionPurchase
from billing.services.commissions import (
    calculate_commission,
    create_commission_checkout,
    get_previous_month_alert_for_user,
    process_commission_payment,
    sync_commission_for_seller,
)
from billing.services.subscription_dates import calculate_new_end_date, normalize_to_midday


class BillingPermissionsTests(TestCase):
    def setUp(self):
        self.plan = MembershipPlan.objects.create(
            name="Plan Base",
            duration_days=30,
            period_unit="day",
            period_count=30,
            price=Decimal("100.00"),
            is_active=True,
        )
        self.sim = SimCard.objects.create(iccid="8901000000000000001", status="Disabled")
        self.assign_url = reverse("billing:assign_plan", args=[self.sim.id])

    def test_non_matriz_cannot_assign_plan(self):
        user = User.objects.create_user(
            username="distribuidor@example.com",
            email="distribuidor@example.com",
            password="testpass123",
            user_type="DISTRIBUIDOR",
        )
        self.client.force_login(user)

        response = self.client.post(self.assign_url, {"plan_id": self.plan.id})

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Subscription.objects.filter(sim=self.sim).exists())

    @patch("billing.views.ensure_sim_enabled", return_value=True)
    def test_matriz_can_assign_plan(self, ensure_sim_enabled_mock):
        user = User.objects.create_user(
            username="matriz@example.com",
            email="matriz@example.com",
            password="testpass123",
            user_type="MATRIZ",
        )
        self.client.force_login(user)

        response = self.client.post(self.assign_url, {"plan_id": self.plan.id})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Subscription.objects.filter(sim=self.sim, plan=self.plan, status="active").exists())
        ensure_sim_enabled_mock.assert_called_once()

    def test_monthly_plan_uses_exactly_30_days_even_with_month_period(self):
        plan = MembershipPlan.objects.create(
            name="Mensual",
            duration_days=30,
            period_unit="month",
            period_count=1,
            price=Decimal("200.00"),
            is_active=True,
        )
        start_date = datetime(2026, 1, 31, 9, 0, tzinfo=timezone.get_current_timezone())

        end_date = calculate_new_end_date(start_date, plan)

        self.assertEqual(end_date, normalize_to_midday(start_date + timedelta(days=30)))


class CommissionTests(TestCase):
    def setUp(self):
        self.plan = MembershipPlan.objects.create(
            name="Plan Base",
            duration_days=30,
            period_unit="day",
            period_count=30,
            price=Decimal("100.00"),
            is_active=True,
        )
        self.matriz = User.objects.create_user(
            username="matriz@example.com",
            email="matriz@example.com",
            password="testpass123",
            user_type="MATRIZ",
        )
        self.distributor_user = User.objects.create_user(
            username="dist@example.com",
            email="dist@example.com",
            password="testpass123",
            user_type="DISTRIBUIDOR",
        )
        self.distribuidor = Distribuidor.objects.create(
            user=self.distributor_user,
            first_name="Dist",
            last_name="Uno",
            email=self.distributor_user.email,
            phone_number="+52 5510000001",
            company="Distribuidor Uno",
            street="Street",
            city="City",
            state="State",
            zip="12345",
            country="MX",
        )
        self.reseller_user = User.objects.create_user(
            username="reseller@example.com",
            email="reseller@example.com",
            password="testpass123",
            user_type="REVENDEDOR",
        )
        self.revendedor = Revendedor.objects.create(
            user=self.reseller_user,
            distribuidor=self.distribuidor,
            first_name="Rev",
            last_name="Uno",
            email=self.reseller_user.email,
            phone_number="+52 5510000002",
            company="Revendedor Uno",
            street="Street",
            city="City",
            state="State",
            zip="12345",
            country="MX",
        )
        self.customer_user = User.objects.create_user(
            username="cliente-commission@example.com",
            email="cliente-commission@example.com",
            password="testpass123",
            user_type="CLIENTE",
        )
        self.cliente = Cliente.objects.create(
            user=self.customer_user,
            distribuidor=self.distribuidor,
            revendedor=self.revendedor,
            first_name="Cliente",
            last_name="Uno",
            email=self.customer_user.email,
            phone_number="+52 5510000003",
            company="Cliente Uno",
            street="Street",
            city="City",
            state="State",
            zip="12345",
            country="MX",
        )
        self.sim = SimCard.objects.create(iccid="8901000000000000999", status="Disabled")
        cliente_ct = ContentType.objects.get_for_model(Cliente)
        SIMAssignation.objects.create(sim=self.sim, content_type=cliente_ct, object_id=self.cliente.id)

    def create_sale(self, *, amount="100.00", status="approved", seller_type="revendedor", payment_id="pay-1"):
        purchase = SubscriptionPurchase.objects.create(
            user=self.customer_user,
            sim=self.sim,
            plan=self.plan,
            action="renew",
            status="approved" if status == "approved" else "pending",
            amount=Decimal(amount),
            currency="MXN",
            mp_payment_id=payment_id,
            mp_status=status,
            mp_account_type=seller_type,
            mp_account_id=self.revendedor.id if seller_type == "revendedor" else self.distribuidor.id,
        )
        return DistributorSale.objects.create(
            distribuidor=self.distribuidor,
            revendedor=self.revendedor,
            cliente=self.cliente,
            purchase=purchase,
            plan=self.plan,
            amount=Decimal(amount),
            currency="MXN",
            payment_id=payment_id,
            paid_at=datetime(2026, 6, 15, 12, 0, tzinfo=timezone.get_current_timezone()),
            status=status,
            period="2026-06",
        )

    def test_commission_calculation_uses_25_percent_decimal(self):
        self.assertEqual(calculate_commission(Decimal("1000.00")), Decimal("250.00"))

    def test_monthly_summary_counts_only_approved_sales(self):
        self.create_sale(amount="1000.00", status="approved", payment_id="approved-1")
        self.create_sale(amount="500.00", status="pending", payment_id="pending-1")

        record = sync_commission_for_seller("revendedor", self.revendedor.id, 2026, 6)

        self.assertEqual(record.total_vendido, Decimal("1000.00"))
        self.assertEqual(record.renewal_count, 1)
        self.assertEqual(record.comision_calculada, Decimal("250.00"))

    def test_matriz_can_access_commission_summary(self):
        self.client.force_login(self.matriz)

        response = self.client.get(reverse("mercado_pago_commissions"), {"month": "06", "year": "2026"})

        self.assertEqual(response.status_code, 200)

    def test_non_matriz_cannot_access_commission_summary(self):
        self.client.force_login(self.distributor_user)

        response = self.client.get(reverse("mercado_pago_commissions"), {"month": "06", "year": "2026"})

        self.assertEqual(response.status_code, 403)

    def test_matriz_can_block_and_unblock_seller(self):
        self.create_sale(amount="1000.00")
        self.client.force_login(self.matriz)
        action_url = reverse("mercado_pago_commission_action", args=["revendedor", self.revendedor.id])

        block_response = self.client.post(action_url, {"month": "06", "year": "2026", "action": "block"})
        self.assertEqual(block_response.status_code, 302)
        record = CommissionPeriod.objects.get(revendedor=self.revendedor, month=6, year=2026)
        self.assertEqual(record.status, CommissionPeriod.STATUS_BLOCKED)

        unblock_response = self.client.post(action_url, {"month": "06", "year": "2026", "action": "unblock"})
        self.assertEqual(unblock_response.status_code, 302)
        record.refresh_from_db()
        self.assertEqual(record.status, CommissionPeriod.STATUS_PENDING)

    def test_blocked_seller_cannot_access_panel(self):
        CommissionPeriod.objects.create(
            revendedor=self.revendedor,
            month=6,
            year=2026,
            total_vendido=Decimal("1000.00"),
            comision_calculada=Decimal("250.00"),
            status=CommissionPeriod.STATUS_BLOCKED,
        )
        self.client.force_login(self.reseller_user)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("commission_blocked"))

    @patch("customer_portal.views.create_checkout_for_plan", return_value="https://checkout.example.com")
    def test_blocked_seller_prevents_customer_checkout(self, create_checkout_mock):
        CommissionPeriod.objects.create(
            revendedor=self.revendedor,
            month=6,
            year=2026,
            total_vendido=Decimal("1000.00"),
            comision_calculada=Decimal("250.00"),
            status=CommissionPeriod.STATUS_BLOCKED,
        )
        self.client.force_login(self.customer_user)

        response = self.client.post(reverse("customer_portal:create_checkout", args=[self.sim.id]), {"plan_id": self.plan.id})

        self.assertEqual(response.status_code, 302)
        create_checkout_mock.assert_not_called()

    def test_first_seven_days_alert_for_previous_month_pending_commission(self):
        self.create_sale(amount="1000.00")
        today = datetime(2026, 7, 3, tzinfo=timezone.get_current_timezone()).date()

        alert = get_previous_month_alert_for_user(self.reseller_user, today=today)

        self.assertIsNotNone(alert)
        self.assertEqual(alert.comision_calculada, Decimal("250.00"))

    @patch(
        "billing.services.commissions.MercadoPagoClient.create_preference",
        return_value={"id": "pref-commission", "init_point": "https://mercadopago.example/checkout"},
    )
    def test_commission_checkout_sends_payment_to_owner_account(self, create_preference_mock):
        self.create_sale(amount="1000.00")
        record = sync_commission_for_seller("revendedor", self.revendedor.id, 2026, 6)

        checkout_url = create_commission_checkout(
            record=record,
            user=self.reseller_user,
            base_url="https://panel.1iox.com",
            notification_url="https://panel.1iox.com/billing/mercadopago/notification/",
        )

        self.assertEqual(checkout_url, "https://mercadopago.example/checkout")
        payload = create_preference_mock.call_args.args[0]
        self.assertEqual(payload["external_reference"], f"commission:{record.id}")
        self.assertEqual(payload["items"][0]["unit_price"], 250.0)
        record.refresh_from_db()
        self.assertEqual(record.mp_preference_id, "pref-commission")

    def test_commission_payment_webhook_marks_period_paid(self):
        self.create_sale(amount="1000.00")
        record = sync_commission_for_seller("revendedor", self.revendedor.id, 2026, 6)

        processed = process_commission_payment(
            {
                "id": "commission-payment-1",
                "status": "approved",
                "external_reference": f"commission:{record.id}",
            }
        )

        self.assertTrue(processed)
        record.refresh_from_db()
        self.assertEqual(record.status, CommissionPeriod.STATUS_PAID)
        self.assertEqual(record.mp_payment_id, "commission-payment-1")
