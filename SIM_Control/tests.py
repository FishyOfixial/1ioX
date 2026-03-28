import json
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from auditlogs.models import SystemLog
from SIM_Control.models import Cliente, Distribuidor, SIMAssignation, SimCard, User


class SecurityTestMixin:
    user_counter = 0
    sim_counter = 0

    def create_profile(self, user_type, *, distribuidor=None, revendedor=None):
        self.__class__.user_counter += 1
        index = self.__class__.user_counter
        email = f"{user_type.lower()}{index}@example.com"
        user = User.objects.create_user(
            username=email,
            email=email,
            password="testpass123",
            first_name=f"Name{index}",
            last_name=f"Last{index}",
            user_type=user_type,
        )
        base_kwargs = {
            "user": user,
            "first_name": f"Name{index}",
            "last_name": f"Last{index}",
            "email": email,
            "phone_number": f"+52 555000{index:04d}",
            "company": f"Company {index}",
            "rfc": f"RFC{index:06d}"[:13],
            "street": "Street",
            "city": "City",
            "state": "State",
            "zip": f"{10000 + index}",
            "country": "MX",
        }
        if user_type == "DISTRIBUIDOR":
            profile = Distribuidor.objects.create(**base_kwargs)
        elif user_type == "CLIENTE":
            profile = Cliente.objects.create(
                distribuidor=distribuidor,
                revendedor=revendedor,
                **{key: value for key, value in base_kwargs.items() if key != "rfc"},
            )
        else:
            raise ValueError(f"Unsupported user type for test helper: {user_type}")
        return user, profile

    def create_sim(self, *assigned_profiles):
        self.__class__.sim_counter += 1
        sim = SimCard.objects.create(
            iccid=f"8901000000000000{self.__class__.sim_counter:03d}",
            status="Disabled",
            label=f"SIM {self.__class__.sim_counter}",
        )
        for profile in assigned_profiles:
            ct = ContentType.objects.get_for_model(profile.__class__)
            SIMAssignation.objects.create(sim=sim, content_type=ct, object_id=profile.id)
        return sim


class SecurityAuthorizationTests(SecurityTestMixin, TestCase):
    def setUp(self):
        self.actor_user, self.actor_distribuidor = self.create_profile("DISTRIBUIDOR")
        self.managed_client_user, self.managed_client = self.create_profile(
            "CLIENTE",
            distribuidor=self.actor_distribuidor,
        )
        self.foreign_distribuidor_user, self.foreign_distribuidor = self.create_profile("DISTRIBUIDOR")
        self.foreign_client_user, self.foreign_client = self.create_profile(
            "CLIENTE",
            distribuidor=self.foreign_distribuidor,
        )
        self.authorized_sim = self.create_sim(self.actor_distribuidor)
        self.foreign_sim = self.create_sim(self.foreign_distribuidor)
        self.client.force_login(self.actor_user)

    def test_update_user_account_rejects_out_of_scope_user(self):
        response = self.client.post(
            reverse("update_user_account", args=[self.foreign_client_user.id]),
            {"action": "active"},
        )

        self.assertEqual(response.status_code, 403)
        self.foreign_client_user.refresh_from_db()
        self.assertTrue(self.foreign_client_user.is_active)

    def test_update_user_rejects_out_of_scope_user(self):
        response = self.client.post(
            reverse("update_user", args=[self.foreign_client_user.id]),
            {
                "first_name": "Blocked",
                "last_name": "User",
                "email": self.foreign_client_user.email,
            },
        )

        self.assertEqual(response.status_code, 403)
        self.foreign_client_user.refresh_from_db()
        self.assertNotEqual(self.foreign_client_user.first_name, "Blocked")

    def test_assign_sims_rejects_out_of_scope_sim(self):
        response = self.client.post(
            reverse("assign_sims"),
            {
                "user_id": str(self.managed_client_user.id),
                "sim_ids": [self.foreign_sim.iccid],
            },
        )

        self.assertEqual(response.status_code, 403)
        client_ct = ContentType.objects.get_for_model(Cliente)
        self.assertFalse(
            SIMAssignation.objects.filter(
                sim=self.foreign_sim,
                content_type=client_ct,
                object_id=self.managed_client.id,
            ).exists()
        )

    def test_assign_sims_accepts_authorized_target_and_sim(self):
        response = self.client.post(
            reverse("assign_sims"),
            {
                "user_id": str(self.managed_client_user.id),
                "sim_ids": [self.authorized_sim.iccid],
            },
        )

        self.assertEqual(response.status_code, 302)
        client_ct = ContentType.objects.get_for_model(Cliente)
        self.assertTrue(
            SIMAssignation.objects.filter(
                sim=self.authorized_sim,
                content_type=client_ct,
                object_id=self.managed_client.id,
            ).exists()
        )

    @patch("SIM_Control.my_views.my_sims.update_sims_status")
    def test_update_sim_state_rejects_out_of_scope_sim(self, update_sims_status_mock):
        response = self.client.post(
            reverse("update_sim_state"),
            {
                "status": "Enabled",
                "iccids": json.dumps([self.foreign_sim.iccid]),
                "labels": json.dumps(["Foreign"]),
            },
        )

        self.assertEqual(response.status_code, 403)
        update_sims_status_mock.assert_not_called()

    @patch("SIM_Control.my_views.my_sims.update_sims_status")
    def test_update_sim_state_accepts_authorized_sim(self, update_sims_status_mock):
        response = self.client.post(
            reverse("update_sim_state"),
            {
                "status": "Enabled",
                "iccids": json.dumps([self.authorized_sim.iccid]),
                "labels": json.dumps(["Renamed"]),
            },
        )

        self.assertEqual(response.status_code, 302)
        update_sims_status_mock.assert_called_once_with(
            [self.authorized_sim.iccid],
            ["Renamed"],
            "Enabled",
        )
        self.authorized_sim.refresh_from_db()
        self.assertEqual(self.authorized_sim.status, "Enabled")
        self.assertEqual(self.authorized_sim.label, "Renamed")


class SecurityRedirectTests(SecurityTestMixin, TestCase):
    def test_set_language_rejects_external_referer(self):
        user, _profile = self.create_profile("DISTRIBUIDOR")
        self.client.force_login(user)

        response = self.client.get(
            reverse("set_lang", args=["en"]),
            HTTP_REFERER="https://evil.example.com/landing",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("dashboard"))
        self.assertTrue(
            SystemLog.objects.filter(message="Unsafe redirect target rejected").exists()
        )


class LoginRateLimitTests(SecurityTestMixin, TestCase):
    def setUp(self):
        cache.clear()

    @override_settings(
        LOGIN_RATE_LIMIT_FAILURES=2,
        LOGIN_RATE_LIMIT_WINDOW_SECONDS=60,
        LOGIN_RATE_LIMIT_LOCKOUT_SECONDS=120,
    )
    def test_login_rate_limit_blocks_repeated_failures(self):
        user, _profile = self.create_profile("DISTRIBUIDOR")
        login_url = reverse("login")

        first_response = self.client.post(
            login_url,
            {"username": user.email, "password": "wrong-pass"},
        )
        second_response = self.client.post(
            login_url,
            {"username": user.email, "password": "wrong-pass"},
        )
        third_response = self.client.post(
            login_url,
            {"username": user.email, "password": "wrong-pass"},
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 429)
        self.assertEqual(third_response.status_code, 429)
        self.assertTrue(
            SystemLog.objects.filter(message="Login rate limit triggered").exists()
        )
