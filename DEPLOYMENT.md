# OptivEdge Framework Deployment Instructions

OptivEdge is a reusable Django framework package. It is not intended to be deployed directly as a standalone Django project. Downstream Django projects install OptivEdge as a dependency and include its Django app, URLs, templates, and migrations.

## Repository Purpose

This repository provides the shared app-shell framework layer used by every OptivEdge-family project, including:

* the navigation shell (`base.html`, sidebar/menu rendering)
* the optional-app plugin registry (`app_meta.py` / `URL_MOUNT` / `SIDEBAR_SECTION` convention)
* shared UI components (icons, form widget styling, overlay-panel view mixin)
* client/engagement metadata (`ApplicationEnvironment`) and its settings UI
* shared framework URL composition
* framework settings components

Domain-specific packages — OptivEdgeIntegrations (firewall config collection/normalization/storage) and
OptivEdgeAssessments (assessment workflows) — install OptivEdge as a dependency and plug into it via the
`app_meta.py` convention. They do not own any shell/navigation code themselves.

Downstream host projects remain responsible for:

* `manage.py`
* root Django settings
* root URL configuration
* environment variables
* database configuration
* deployment configuration
* project-specific apps and workflows

Use the deployment template below to generate a correctly-wired host project instead of hand-assembling
one — see "Creating a New Engagement Deployment".

## Creating a New Engagement Deployment

`src/optivedge/deployment_template/` is a `django-admin startproject` template (see
[Django's project template docs](https://docs.djangoproject.com/en/6.0/ref/django-admin/#cmdoption-startproject-template))
that generates a `manage.py`/`settings.py`/`urls.py` already wired for the full OptivEdge stack (OptivEdge +
OptivEdgeIntegrations + OptivEdgeAssessments), plus a `wheels/` directory that holds every wheel the
generated project needs — so a new engagement environment can be stood up fully offline.

**It SHIPS INSIDE the optivedge wheel**, so a machine that has installed the stack already has the template
and needs no checkout of this repo. It used to live at the repository root, outside `src/`, which meant
setuptools never packaged it and a new environment had to fetch it from GitHub — awkward, since these repos
are private.

### Creating a new engagement, online

The target needs GitHub credentials, because the three repositories are private (`gh auth login`, or a PAT
in a git credential helper).

```bash
mkdir ~/SomeClient && cd ~/SomeClient
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

# 1. The stack. This is also what installs Django, which the next step needs.
python -m pip install "git+https://github.com/JasonBarrett77/OptivEdgeAssessments.git@main#egg=optivedge-assessments"

# 2. The project, from the template inside the package just installed.
OPTIVEDGE=$(python -c "import optivedge; print(optivedge.__path__[0])")
django-admin startproject someclient . --template="$OPTIVEDGE/deployment_template"

# 3. Database.
python manage.py migrate
python manage.py createsuperuser

# 4. Engagement metadata, then the control catalog - in that order.
python manage.py runserver     # open http://127.0.0.1:8000/ and use "Configure"
python manage.py apply_controls_catalog --apply
```

**Two steps, and nothing quoted inside the Python.** This was one line with a nested
`python -c '... "deployment_template" ...'` inside `--template="$( )"`, which works in bash and
breaks everywhere else: PowerShell and `cmd` strip the inner double quotes, Python then sees a
bare identifier, and the error is `NameError: name 'deployment_template' is not defined` with
Python 3.11+ underlining the whole name. It reads like a broken install and is a quoting bug.
The variable holds the package directory, the shell appends the subdirectory, and no quotes
cross a shell boundary. In PowerShell:

```powershell
$optivedge = python -c "import optivedge; print(optivedge.__path__[0])"
django-admin startproject someclient . --template="$optivedge\deployment_template"
```

**Install before `startproject`, not after.** `django-admin` does not exist until Django is installed, and
Django arrives with the packages.

**Apply the catalog after configuring the engagement.** A fresh database holds no controls at all, so every
assessment page is empty until this runs — and run before the engagement exists it says "the catalog was
applied but not recorded as current".

### On Windows, in PowerShell

The engagement procedures above and below are written for bash. A new engagement machine is as
likely to be Windows as not — one hit this on 2026-10-05 — and three of those lines are POSIX
only. Substitute, and everything else is identical:

| bash | PowerShell |
| --- | --- |
| `python3.12 -m venv .venv` | `py -3.12 -m venv .venv` |
| `source .venv/bin/activate` | `.venv\Scripts\Activate.ps1` |
| `OPTIVEDGE=$(python -c "…")` | `$optivedge = python -c "…"` |

Written out, the venv and template steps:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
# ... step 1 as written ...
$optivedge = python -c "import optivedge; print(optivedge.__path__[0])"
django-admin startproject someclient . --template="$optivedge\deployment_template"
```

`python3.12` does not exist on Windows; `py` is the version launcher that ships with the
python.org installer, and `py -3.12` is how a specific version is selected. Plain `python`
works too when 3.12 is the only one installed, which is worth not assuming.

**If activation is refused**, the execution policy is blocking the script rather than anything
being wrong with the venv:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Process scope, so it lasts for that window only and changes nothing for the machine. The
default `RemoteSigned` already permits a locally generated `Activate.ps1`; a machine set to
`Restricted` is the one that needs this.

Everything after the venv - `pip`, `django-admin`, `manage.py` - is the same in both shells.

### Building the offline bundle (run this on a machine with PyPI/GitHub access)

```bash
cd ~/PythonProjects/OptivEdge
git status                 # commit and push OptivEdge, OptivEdgeIntegrations, and
git push                   # OptivEdgeAssessments first -- the build resolves each
                            # package's own dependency (e.g. OptivEdgeAssessments'
                            # "optivedge @ git+https://...@main") from GitHub, so
                            # uncommitted/unpushed local changes will not be included.
./scripts/build_deployment_bundle.sh
```

This populates `src/optivedge/deployment_template/wheels/` with wheels for OptivEdge, OptivEdgeIntegrations,
OptivEdgeAssessments, and every one of their public PyPI dependencies (Django, requests, xmltodict,
python-docx, docxtpl, XlsxWriter, and their transitive dependencies). At that point that directory is
self-contained — copy it (or zip it) to the target environment; no further network access is required there.

### Creating a new engagement, offline

Nothing here needs GitHub, a credential, or a checkout — only the copied template directory.

```bash
mkdir ~/SomeClient && cd ~/SomeClient
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

# Django first, from the bundled wheels: startproject cannot run without it.
python -m pip install --no-index --find-links=/path/to/deployment_template/wheels Django
django-admin startproject someclient . --template=/path/to/deployment_template

# The wheels ride inside the generated project, so this works from the project root.
python -m pip install --no-index --find-links=wheels optivedge optivedge-integrations optivedge-assessments

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver     # Configure the engagement
python manage.py apply_controls_catalog --apply
```

### Template maintenance notes

* Files ending `-tpl` are rendered by Django's template engine (`{{ project_name }}`, `{{ secret_key }}`,
  `{{ django_version }}`, `{{ docs_version }}` placeholders); everything else (including `.whl` files) is
  copied byte-for-byte, since Django only renders files matching its `extensions` list (`.py` by default).
* The `project_name/` directory itself gets renamed to the actual project name — this is Django's own
  `startproject` convention, not something specific to this template.
* If a new domain package is added to the stack in the future, add its `OPTIVEDGE_<NAME>_APPS` import/splice
  to `src/optivedge/deployment_template/project_name/settings.py-tpl` and its wheel to
  `scripts/build_deployment_bundle.sh`.

## Package Layout

Expected repository structure:

```text
OptivEdge/
├── pyproject.toml
├── DEPLOYMENT.md
├── CLAUDE.md
├── src/
│   └── optivedge/
│       ├── __init__.py
│       ├── apps.py
│       ├── models.py
│       ├── views.py
│       ├── forms.py
│       ├── urls.py
│       ├── migrations/
│       ├── app_registry.py
│       ├── context_processors.py
│       ├── settings/
│       │   ├── __init__.py
│       │   └── components.py
│       ├── templates/
│       └── templatetags/
│       ├── deployment_template/      <- shipped in the wheel
│       │   ├── manage.py-tpl
│       │   ├── wheels/
│       │   └── project_name/
│       │       ├── settings.py-tpl
│       │       ├── urls.py-tpl
│       │       ├── wsgi.py-tpl
│       │       └── asgi.py-tpl
├── scripts/
│   └── build_deployment_bundle.sh
└── .gitignore
```

## Version Requirements

OptivEdge currently targets:

```text
Python >= 3.12
Django >= 6.0, < 6.1
```

The Django dependency should be declared in `pyproject.toml`:

```toml
[project]
requires-python = ">=3.12"
dependencies = [
    "Django>=6.0,<6.1",
]
```

## Installing OptivEdge in a Downstream Project

Create and activate a virtual environment in the downstream project:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Install OptivEdge from GitHub:

```bash
python -m pip install "git+https://github.com/JasonBarrett77/OptivEdge.git@main#egg=optivedge"
```

For repeatable installs, prefer a tag:

```bash
python -m pip install "git+https://github.com/JasonBarrett77/OptivEdge.git@v0.1.0#egg=optivedge"
```

For local development against a checked-out copy:

```bash
python -m pip install -e ~/PythonProjects/OptivEdge
```

### Co-development with local checkouts of the whole stack

Installing the three packages editable **in one `pip install` command fails** with `ResolutionImpossible`.
OptivEdgeIntegrations and OptivEdgeAssessments declare their `optivedge` dependency as a GitHub URL, and pip
treats that as a different distribution from a local editable install of the same package — so requesting
both in one resolution is a genuine conflict, not a pip bug to work around with flags.

Install in stages instead, outermost dependency first, using `--no-deps` on the packages whose git-URL
dependencies are already satisfied by an editable:

```bash
# 1. OptivEdge first, with its real dependencies (this is what installs Django).
python -m pip install -e ~/PythonProjects/OptivEdge

# 2+3. The domain packages, skipping their declared git-URL dependency on OptivEdge --
#      the editable from step 1 already satisfies it.
python -m pip install -e ~/PythonProjects/OptivEdgeIntegrations --no-deps
python -m pip install -e ~/PythonProjects/OptivEdgeAssessments --no-deps

# 4. The public dependencies that --no-deps skipped.
python -m pip install requests xmltodict python-docx docxtpl XlsxWriter
```

`pip list` should then show all three as editable paths into `~/PythonProjects/`, and changes in any `src/`
tree take effect without reinstalling.

## Configuring a Downstream Django Project

Create a normal Django project:

```bash
django-admin startproject config .
```

Edit `config/settings.py`.

Import OptivEdge's settings components, plus one apps component per domain package the deployment installs.
Each package exports exactly one such name; only OptivEdge exports context processors and template libraries,
because only OptivEdge owns the shell:

```python
from optivedge.settings.components import (
    OPTIVEDGE_APPS,
    OPTIVEDGE_CONTEXT_PROCESSORS,
    OPTIVEDGE_TEMPLATE_LIBRARIES,
)
from optivedge_integrations.settings.components import OPTIVEDGE_INTEGRATIONS_APPS
from assessments.settings.components import OPTIVEDGE_ASSESSMENTS_APPS
```

Add OptivEdge apps to `INSTALLED_APPS`, followed by whichever domain packages (OptivEdgeIntegrations,
OptivEdgeAssessments) the deployment needs:

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    *OPTIVEDGE_APPS,
    *OPTIVEDGE_INTEGRATIONS_APPS,
    *OPTIVEDGE_ASSESSMENTS_APPS,
]
```

This is the order `src/optivedge/deployment_template/project_name/settings.py-tpl` generates, and it is the order to keep.
`INSTALLED_APPS` order decides which app wins a template path collision (first match wins in the
app-directories loader) — there are currently **no** template-name collisions across the three packages, so
nothing depends on the order today. Reordering it to let a domain package override a shell template would be
a silent, action-at-a-distance override; put the override in OptivEdge instead, where it is visible to every
deployment.

Configure templates:

```python
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "libraries": {
                **OPTIVEDGE_TEMPLATE_LIBRARIES,
            },
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                *OPTIVEDGE_CONTEXT_PROCESSORS,
            ],
        },
    },
]
```

Edit `config/urls.py`:

```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("optivedge.urls")),
    path("admin/", admin.site.urls),
]
```

`optivedge.urls` owns the root URL namespace (`home`, `application_environment_settings`) and composes every
other installed app's routes via the plugin registry — domain packages should not attempt to own root.

## Running Django Checks and Migrations

From the downstream project root:

```bash
python manage.py check
python manage.py migrate
```

Expected migrations include the OptivEdge `optivedge` app:

```text
Applying optivedge.0001_initial... OK
```

## Running the Development Server

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

If the OptivEdge home page renders (with the "Set Client Settings"/"Configure" prompt), the framework
package, app config, URL config, templates, and migrations are working.

## Development Workflow for OptivEdge

When changing OptivEdge itself:

```bash
cd ~/PythonProjects/OptivEdge
source .venv/bin/activate
```

Install the framework editable for local validation:

```bash
python -m pip install -e .
```

Run a basic non-Django import check:

```bash
python - <<'PY'
import optivedge
import optivedge.app_registry
import optivedge.context_processors
import optivedge.templatetags.lucide

print("OptivEdge non-Django import check passed")
PY
```

Django model imports require a configured Django settings module. Validate full Django behavior from a
downstream test project using:

```bash
python manage.py check
python manage.py migrate
python manage.py runserver
```

## Optional-App Plugin Convention

Any installed app may expose a small `app_meta.py` module at its package root with:

```python
URL_MOUNT = {"prefix": "some-prefix/", "module": "some_app.urls"}
SIDEBAR_SECTION = {
    "label": "Section Label",
    "items": [
        {"href": "/some-prefix/thing/", "icon": "server", "label": "Thing", "active_names": {"thing_list"}},
    ],
}
```

`optivedge.app_registry.optional_app_urlpatterns()` and `sidebar_sections()` walk every installed app looking
for this module — this is how OptivEdgeIntegrations and OptivEdgeAssessments plug their routes and navigation
into the shared shell without OptivEdge needing to know about them ahead of time.

## Template Organization

Shared framework templates live under:

```text
src/optivedge/templates/
```

The root OptivEdge app must be installed so Django can discover shared templates:

```python
OPTIVEDGE_APPS = [
    "optivedge.apps.OptivEdgeConfig",
]
```

Domain packages own their own templates under their own app's `templates/` directory (e.g.
`optivedge_integrations/integrations/templates/integrations/`) and can still `{% include %}`/`{% extends %}`
shared OptivEdge templates (`base.html`, `components/...`) — Django's app-directories template loader
resolves by relative path across every installed app, not by Python package boundaries.

## Django App Labels

This app intentionally has a short, stable label:

```python
class OptivEdgeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "optivedge"
    label = "optivedge"
```

This preserves model labels such as:

```text
optivedge.ApplicationEnvironment
```

Do not rename the app label casually. Changing it would affect migrations, content types, and foreign keys.

## Publishing a Version

Only tag a release after a downstream Django project can successfully run:

```bash
python manage.py check
python manage.py migrate
python manage.py runserver
```

Create and push a tag:

```bash
cd ~/PythonProjects/OptivEdge
git status
git tag v0.1.0
git push origin v0.1.0
```

Downstream projects should then pin the tag:

```text
git+https://github.com/JasonBarrett77/OptivEdge.git@v0.1.0#egg=optivedge
```

## Troubleshooting

### `TemplateDoesNotExist: workspace.html`

Cause: the `optivedge` Django app is not installed.

Confirm `OPTIVEDGE_APPS` includes:

```python
"optivedge.apps.OptivEdgeConfig"
```

### `NoReverseMatch` for a domain-package URL name

Cause: a domain package's `app_meta.py` is missing, or its `URL_MOUNT` module path is wrong. Confirm the
package exposes an `app_meta.py` with a correct `URL_MOUNT`, and that it's actually installed in
`INSTALLED_APPS`.

### `ImproperlyConfigured: Requested setting INSTALLED_APPS`

Cause: Django models were imported outside a configured Django project.

This is expected if running plain Python imports against model modules. Validate models from a configured
downstream Django project using:

```bash
python manage.py check
```

### SSH install fails with `Permission denied (publickey)`

Use HTTPS:

```bash
python -m pip install "git+https://github.com/JasonBarrett77/OptivEdge.git@main#egg=optivedge"
```

Or configure SSH keys for the current WSL/Linux environment.

## Minimal Downstream `requirements.txt`

```text
git+https://github.com/JasonBarrett77/OptivEdge.git@v0.1.0#egg=optivedge
```

During active development, a downstream project may temporarily use:

```text
git+https://github.com/JasonBarrett77/OptivEdge.git@main#egg=optivedge
```

Production or repeatable builds should use a tag or commit SHA, not floating `main`.
