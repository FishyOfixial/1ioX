from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from SIM_Control.models import SimCard, User
from billing.models import MembershipPlan, Subscription
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
