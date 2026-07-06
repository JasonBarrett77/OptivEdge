"""Shared form widget styling and the application-environment form.

TEXT_INPUT_CLASS/MONO_TEXT_INPUT_CLASS/TEXTAREA_CLASS are also used by domain
apps (e.g. OptivEdgeIntegrations' ManagementStationForm) — keep this a stable,
generic design-system surface rather than coupling it to any one form.
"""

from django import forms

from .models import ApplicationEnvironment


TEXT_INPUT_CLASS = (
    "h-8 rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-800 "
    "placeholder:text-slate-400 focus:border-blue-300 focus:outline-none "
    "focus:ring-2 focus:ring-blue-500/20"
)
MONO_TEXT_INPUT_CLASS = f"{TEXT_INPUT_CLASS} font-mono"
TEXTAREA_CLASS = (
    "min-h-24 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm "
    "text-slate-800 placeholder:text-slate-400 focus:border-blue-300 "
    "focus:outline-none focus:ring-2 focus:ring-blue-500/20"
)


class ApplicationEnvironmentForm(forms.ModelForm):
    class Meta:
        model = ApplicationEnvironment
        fields = [
            "client_name",
            "client_short_name",
            "opportunity_number",
            "notes",
        ]
        widgets = {
            "client_name": forms.TextInput(
                attrs={
                    "class": TEXT_INPUT_CLASS,
                }
            ),
            "client_short_name": forms.TextInput(
                attrs={
                    "class": MONO_TEXT_INPUT_CLASS,
                }
            ),
            "opportunity_number": forms.TextInput(
                attrs={
                    "class": MONO_TEXT_INPUT_CLASS,
                    "placeholder": "OP-1234567",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASS,
                }
            ),
        }
