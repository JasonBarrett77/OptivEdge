"""Shell views: the home dashboard, client/engagement settings, and shared view mixins.

RightOverlayMixin is also used by domain apps (e.g. OptivEdgeIntegrations'
management-station create/update/delete views) — keep it generic.
"""

from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import TemplateView

from .forms import ApplicationEnvironmentForm
from .models import ApplicationEnvironment


def get_application_environment():
    application_environments = list(ApplicationEnvironment.objects.order_by("pk")[:2])
    if len(application_environments) > 1:
        raise ImproperlyConfigured("Expected a single ApplicationEnvironment record for this deployment.")
    return application_environments[0] if application_environments else None


class RightOverlayMixin:
    overlay_close_url = None
    overlay_panel_class = "w-[32rem] max-w-[calc(100vw-15rem)]"

    def get_overlay_close_url(self):
        return self.overlay_close_url

    def get_overlay_panel_class(self):
        return self.overlay_panel_class

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["overlay_is_open"] = True
        context["overlay_close_url"] = self.get_overlay_close_url()
        context["overlay_panel_class"] = self.get_overlay_panel_class()
        return context


class HomeBackgroundMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["application_environment"] = get_application_environment()
        return context


class HomeView(TemplateView):
    template_name = "workspace.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["application_environment"] = get_application_environment()
        return context


class ApplicationEnvironmentSettingsView(RightOverlayMixin, HomeBackgroundMixin, TemplateView):
    template_name = "application_environment_form.html"
    overlay_close_url = "/"

    def get_application_environment(self):
        return get_application_environment()

    def get_form(self, instance=None, data=None):
        return ApplicationEnvironmentForm(instance=instance, data=data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application_environment = kwargs.pop("application_environment", None) or self.get_application_environment()
        form = kwargs.pop("form", None) or self.get_form(instance=application_environment)
        context["application_environment"] = application_environment
        context["form"] = form
        context["form_mode"] = "update" if application_environment is not None else "create"
        return context

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        application_environment = self.get_application_environment()
        form = self.get_form(instance=application_environment, data=request.POST)
        if not form.is_valid():
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    application_environment=application_environment,
                )
            )

        self.object = form.save()
        messages.success(request, "Client environment settings saved.")
        return HttpResponseRedirect(reverse("home"))
