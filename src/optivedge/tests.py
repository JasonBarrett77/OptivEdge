from types import SimpleNamespace
from unittest import mock

from django.core.exceptions import ValidationError
from django.template import Context, Template
from django.test import RequestFactory, TestCase
from django.urls import ResolverMatch, reverse

from optivedge.app_registry import sidebar_sections
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


class DeploymentTemplateTests(TestCase):
    """The engagement project template ships inside the wheel.

    It lived at the repository ROOT until 2026-09-25, outside `src/`, so setuptools packaged
    none of it: an installed optivedge did not carry the thing that generates a project
    around it, and a new environment had to fetch it from GitHub. These repositories are
    private, so that meant credentials on every machine that wanted to stand one up.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import pathlib

        import optivedge

        cls.package = pathlib.Path(optivedge.__file__).resolve().parent
        cls.template = cls.package / "deployment_template"
        cls.pyproject = cls.package.parents[1] / "pyproject.toml"

    def test_the_template_lives_inside_the_package(self):
        """`django-admin startproject --template=<this>` has to work from an INSTALLED
        optivedge, which means the path is relative to the module, not to a checkout."""
        self.assertTrue(self.template.is_dir(), self.template)

    def test_it_holds_everything_startproject_needs(self):
        for name in (
            "manage.py-tpl",
            "project_name/settings.py-tpl",
            "project_name/urls.py-tpl",
            "project_name/wsgi.py-tpl",
            "project_name/asgi.py-tpl",
            "project_name/__init__.py-tpl",
        ):
            self.assertTrue((self.template / name).is_file(), name)

    def test_the_generated_settings_wire_all_three_packages(self):
        settings = (self.template / "project_name" / "settings.py-tpl").read_text(encoding="utf-8")

        for component in ("OPTIVEDGE_APPS", "OPTIVEDGE_INTEGRATIONS_APPS", "OPTIVEDGE_ASSESSMENTS_APPS"):
            self.assertIn(component, settings)

    def test_package_data_names_the_tpl_suffix(self):
        """A `*.py` glob matches NO file in the template - every one ends `-tpl` - so the
        declaration has to say so. Getting this wrong ships an empty directory.
        """
        if not self.pyproject.is_file():
            self.skipTest("installed without the source tree")
        declared = self.pyproject.read_text(encoding="utf-8")

        self.assertIn('"deployment_template/*-tpl"', declared)
        self.assertIn('"deployment_template/**/*-tpl"', declared)


class SidebarSectionTests(TestCase):
    """How separately-installed apps compose ONE rail.

    Two properties, both of which exist so an app never has to name another app's routes:
    sections sharing a label become one heading, and `order` decides where that heading lands
    regardless of which app happened to be installed first.
    """

    def sections(self, *metas):
        with mock.patch("optivedge.app_registry.iter_app_meta", return_value=list(metas)):
            return sidebar_sections()

    def meta(self, section):
        return SimpleNamespace(SIDEBAR_SECTION=section)

    def test_sections_sharing_a_label_become_one_heading(self):
        """Notes lives in Integrations and Experimental is named by Assessments. Without this,
        the rail shows the heading twice."""
        sections = self.sections(
            self.meta([{"label": "Experimental", "items": [{"label": "Notes"}]}]),
            self.meta([{"label": "Experimental", "items": [{"label": "Plain-Language Query"}]}]))

        self.assertEqual(len(sections), 1)
        self.assertEqual([item["label"] for item in sections[0]["items"]],
                         ["Notes", "Plain-Language Query"])

    def test_order_decides_where_a_merged_section_lands(self):
        """The first contributor would otherwise decide it. Integrations is installed before
        Assessments, so Experimental would sit above the Assessments items."""
        sections = self.sections(
            self.meta([{"label": "Experimental", "order": 100, "items": []},
                       {"label": "Firewall Integrations", "items": []}]),
            self.meta([{"label": "Assessments", "items": []}]))

        self.assertEqual([section["label"] for section in sections],
                         ["Firewall Integrations", "Assessments", "Experimental"])

    def test_one_contributor_is_enough_to_make_a_section_collapsible(self):
        sections = self.sections(
            self.meta([{"label": "Experimental", "items": []}]),
            self.meta([{"label": "Experimental", "collapsible": True, "items": []}]))

        self.assertTrue(sections[0]["collapsible"])

    def test_a_section_knows_the_url_names_of_its_own_items(self):
        """A collapsible section opens on a page inside it, so it needs its items' names.
        Asking every contributor to repeat them at the section level is a list that falls
        behind - this one cannot."""
        sections = self.sections(self.meta([{
            "label": "Experimental",
            "active_names": {"declared_by_the_section"},
            "items": [{"label": "Notes", "active_names": {"note_list", "note_create"}}],
        }]))

        self.assertEqual(sections[0]["active_names"],
                         {"declared_by_the_section", "note_list", "note_create"})

    def test_merging_does_not_grow_an_app_meta_on_every_call(self):
        """The dicts are module-level in each `app_meta`. Appending to one rather than to a
        copy would add an item to the rail on every request."""
        declared = {"label": "Experimental", "items": [{"label": "Notes"}]}
        metas = [self.meta([declared]),
                 self.meta([{"label": "Experimental", "items": [{"label": "Other"}]}])]

        for _ in range(3):
            self.assertEqual(len(self.sections(*metas)[0]["items"]), 2)
        self.assertEqual(len(declared["items"]), 1)


class CollapsibleSidebarRenderingTests(TestCase):
    """`<details>` rather than a button and a class: no JavaScript, and no second source of
    truth about whether the section is open."""

    template = Template("{% extends 'base.html' %}")

    def render(self, section, url_name):
        request = RequestFactory().get("/")
        request.resolver_match = ResolverMatch(lambda r: None, (), {}, url_name=url_name)
        return self.template.render(Context({
            "optional_sidebar_sections": [section], "request": request}))

    def section(self, **overrides):
        return {"label": "Experimental", "collapsible": True,
                "active_names": {"note_list"},
                "items": [{"label": "Notes", "href": "/integrations/notes/", "icon": "book-marked",
                           "active_names": {"note_list"}}],
                **overrides}

    def test_a_collapsible_section_is_closed_on_an_unrelated_page(self):
        html = self.render(self.section(), url_name="home")

        self.assertIn("<details", html)
        self.assertNotIn(" open>", html)
        # Closed, not absent: the items are in the markup and the browser hides them.
        self.assertIn("/integrations/notes/", html)

    def test_it_opens_on_a_page_inside_it(self):
        """Otherwise arriving at a page in a collapsed section shows a rail with no sign of
        where you are."""
        html = self.render(self.section(), url_name="note_list")

        self.assertIn(" open>", html)

    def test_a_plain_section_is_not_a_details(self):
        html = self.render(self.section(collapsible=False), url_name="home")

        self.assertNotIn("<details", html)
        self.assertIn("/integrations/notes/", html)
