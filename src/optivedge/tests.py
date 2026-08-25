from django.core.exceptions import ValidationError
from django.template import Context, Template
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
        self.assertContains(response, "Client Settings")
        self.assertContains(response, "Configure")
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


class LucideIconTagTests(TestCase):
    """The tag accepts **attrs. Before this it applied exactly one of them.

    `{% lucide "x" stroke_width="2.5" %}` parsed, rendered, and did nothing - the worst
    shape a bug can take in a template tag, since the markup looks correct in review.
    """

    def _render(self, template_text: str) -> str:
        return Template("{% load lucide %}" + template_text).render(Context({}))

    def test_class_still_works(self):
        svg = self._render('{% lucide "triangle-alert" class="h-5 w-5" %}')
        self.assertIn('class="h-5 w-5"', svg)

    def test_an_arbitrary_attribute_is_applied(self):
        svg = self._render('{% lucide "triangle-alert" stroke_width="2.5" %}')
        self.assertIn('stroke-width="2.5"', svg)

    def test_underscores_become_hyphens(self):
        """Django parses tag keywords as identifiers, so stroke-width= cannot be written."""
        svg = self._render('{% lucide "triangle-alert" stroke_linecap="square" %}')
        self.assertIn('stroke-linecap="square"', svg)
        self.assertNotIn("stroke_linecap", svg)

    def test_an_existing_attribute_is_replaced_not_duplicated(self):
        """Lucide icons ship with stroke-width="2". Two of one attribute is invalid markup
        whose winner is parser-defined, so an override has to substitute."""
        svg = self._render('{% lucide "triangle-alert" stroke_width="2.5" %}')
        self.assertEqual(svg.count("stroke-width"), 1)
        self.assertNotIn('stroke-width="2"', svg)

    def test_the_health_indicator_renders_thick_and_red(self):
        """The indicator's absence is what reads as all-clear, so its presence must not
        look like decoration. Rendering it here pins the styling against a silent revert."""
        from django.template.loader import render_to_string

        html = render_to_string("base.html", {"app_health_indicators": [
            {"label": "Normalization is incomplete", "url": "/integrations/normalization-issues/"},
        ]})
        self.assertIn("text-red-600", html)
        self.assertIn('stroke-width="2.5"', html)
        self.assertIn('class="h-5 w-5"', html)
