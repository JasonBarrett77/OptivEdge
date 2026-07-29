# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

OptivEdge is a reusable Django **app-shell framework**, not a standalone deployable project. It provides the
shared navigation shell, the optional-app plugin registry, shared UI components, and client/engagement
metadata (`ApplicationEnvironment`) that domain packages — OptivEdgeIntegrations (firewall config
collection/normalization/storage), OptivEdgeAssessments (assessment workflows), and any future ones — plug
into. It is installed as a dependency (`pip install -e .` for local dev, or via git URL) by a separate
downstream Django project that owns `manage.py`, root settings, root URLs, and the database. This repo has
no `manage.py` and no *downstream* Django settings module of its own — Django model/view code cannot be
exercised as part of a real deployment without a configured downstream project. It does have a committed
`tests/settings.py`, but that exists solely to run this repo's own test suite in isolation (see "Commands").

OptivEdge was extracted out of OptivEdgeIntegrations: that repo's stated purpose is firewall data, but its
root app had accumulated generic shell code (base.html, menu, plugin registry) and `ApplicationEnvironment`
(deployment/engagement metadata, not firewall data) that didn't belong there. OptivEdgeIntegrations and
OptivEdgeAssessments are now peer domain apps that both depend on this package, rather than one depending on
the other's leftovers.

Full downstream integration instructions (installing, wiring `INSTALLED_APPS`/`TEMPLATES`/urls, migrations,
troubleshooting) live in `DEPLOYMENT.md`. Read it before changing anything that affects how downstream
projects or domain packages consume this package (app label, settings components, URL composition, template
locations).

This repo also owns `deployment_template/` — a `django-admin startproject --template=` project template
(not a Python package, not installed by anything) that generates a fully-wired new engagement host project,
and `scripts/build_deployment_bundle.sh`, which builds wheels for all three OptivEdge-family packages plus
their public dependencies into `deployment_template/wheels/` for offline installs. See "Creating a New
Engagement Deployment" in `DEPLOYMENT.md` for the full workflow. If a new domain package is added to the
stack, both files need a matching update (see "Template maintenance notes" in `DEPLOYMENT.md`).

## Commands

Editable install for local development:

```bash
python -m pip install -e .
```

Non-Django import sanity check (validates plain-Python modules only; does not touch Django models):

```bash
python - <<'PY'
import optivedge
import optivedge.app_registry
import optivedge.context_processors
import optivedge.templatetags.lucide
PY
```

Run this repo's own test suite (`src/optivedge/tests.py`) via the committed `tests/settings.py` — a
minimal, test-only settings module (not a downstream integration example; see `tests/settings.py`'s
docstring and `DEPLOYMENT.md` for that):

```bash
DJANGO_SETTINGS_MODULE=tests.settings python -m django test optivedge
```

Validating full downstream Django behavior (models, migrations, views, other installed apps) still requires
a real downstream project:

```bash
python manage.py check
python manage.py migrate
python manage.py runserver
```

## Architecture

### Package/app boundaries

- `optivedge` (label `optivedge`) — the only app in this package. Owns the navigation shell (`base.html`,
  `workspace.html`, `templates/components/`), the optional-app plugin registry (`app_registry.py`), shared
  template tags (`templatetags/lucide.py`), settings composition helpers (`settings/components.py`), and
  `ApplicationEnvironment` (client/engagement metadata) with its view/form/routes (`home`,
  `application_environment_settings`).
- `optivedge.app_registry` provides the plugin convention every domain app uses: any installed app may
  expose an `app_meta.py` with `URL_MOUNT = {"prefix": ..., "module": ...}` and/or `SIDEBAR_SECTION`, picked
  up automatically via `optional_app_urlpatterns()` / `sidebar_sections()`. `optivedge.urls` owns the root
  URL namespace (`home` at `/`, `application_environment_settings` at `/environment/settings/`) and appends
  `optional_app_urlpatterns()` — domain apps should never try to own root themselves.
- `optivedge.views.RightOverlayMixin` and the `TEXT_INPUT_CLASS`/`MONO_TEXT_INPUT_CLASS`/`TEXTAREA_CLASS`
  constants in `optivedge.forms` are shared UI primitives used by domain-app views/forms too (e.g.
  OptivEdgeIntegrations' management-station views and form) — keep them generic, don't couple them to
  `ApplicationEnvironment` specifically even though that's the only consumer defined in this repo.

### Template resolution across packages

Django's app-directories template loader resolves `{% include %}`/`{% extends %}` by relative path across
*every* installed app's `templates/` directory, not by Python package boundaries. Domain packages can
`{% extends "base.html" %}` or `{% include "components/partials/analytical_table_styles.html" %}` without any
import — they just need `optivedge` installed and listed in `INSTALLED_APPS` alongside them. The one
exception is `templatetags/lucide.py`'s icon lookup, which uses `importlib.resources.files("optivedge")`
directly (not the template loader) — icon SVGs must physically live inside this package's
`templates/components/icons/`, not a domain package's.

### Django App Label

`optivedge` is a short, stable label — do not rename it casually. `ApplicationEnvironment`'s migrations,
content types, and any future FK references key off it (`optivedge.ApplicationEnvironment`).
