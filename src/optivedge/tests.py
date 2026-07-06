from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from optivedge.models import ApplicationEnvironment


class EnvironmentModelsTests(TestCase):
    def test_application_environment_requires_opportunity_number_format(self):
        with self.assertRaises(ValidationError):
            ApplicationEnvironment.objects.create(
                client_name="Example Corp",
                client_short_name="EXAMPLE",
                opportunity_number="1234567",
            )

    def test_application_environment_opportunity_number_must_be_unique(self):
        ApplicationEnvironment.objects.create(
            client_name="Example Corp",
            client_short_name="EXAMPLE",
            opportunity_number="OP-1234567",
        )

        with self.assertRaises(ValidationError):
            ApplicationEnvironment.objects.create(
                client_name="Another Corp",
                client_short_name="ANOTHER",
                opportunity_number="OP-1234567",
            )

    def test_application_environment_string_uses_short_name_and_opportunity_number(self):
        environment = ApplicationEnvironment.objects.create(
            client_name="Example Corp",
            client_short_name="EXAMPLE",
            opportunity_number="OP-1234567",
        )

        self.assertEqual(str(environment), "EXAMPLE / OP-1234567")


class ApplicationEnvironmentViewTests(TestCase):
    def test_home_renders_configure_action_when_environment_missing(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Set Client Settings")
        self.assertContains(response, "have not been configured yet")

    def test_settings_post_creates_application_environment(self):
        response = self.client.post(
            reverse("application_environment_settings"),
            {
                "client_name": "Example Corp",
                "client_short_name": "EXAMPLE",
                "opportunity_number": "OP-1234567",
                "notes": "Primary consulting environment",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ApplicationEnvironment.objects.count(), 1)
        application_environment = ApplicationEnvironment.objects.get()
        self.assertEqual(application_environment.client_name, "Example Corp")
        self.assertContains(response, "Client environment settings saved.")
        self.assertContains(response, "Example Corp")

    def test_settings_post_updates_existing_application_environment(self):
        application_environment = ApplicationEnvironment.objects.create(
            client_name="Example Corp",
            client_short_name="EXAMPLE",
            opportunity_number="OP-1234567",
        )

        response = self.client.post(
            reverse("application_environment_settings"),
            {
                "client_name": "Example Corporation",
                "client_short_name": "EXCORP",
                "opportunity_number": "OP-7654321",
                "notes": "Updated notes",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ApplicationEnvironment.objects.count(), 1)
        application_environment.refresh_from_db()
        self.assertEqual(application_environment.client_name, "Example Corporation")
        self.assertEqual(application_environment.client_short_name, "EXCORP")
        self.assertEqual(application_environment.opportunity_number, "OP-7654321")
