# MTMS (Mobiuz Task Management System)

Enterprise-oriented Kanban task board built with **Django 5**, **PostgreSQL** (optional SQLite for local dev), **Redis** (optional cache/session backend), **TailwindCSS**, **Alpine.js**, and **SortableJS**.

## Quick start (SQLite)

```powershell
cd d:\all_projects\mobiuz_project
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000 — sign in and use the Kanban board. Staff/superusers see **Admin Dashboard** plus `/admin/`.

## PostgreSQL & Redis

Set `DATABASE_URL` and optionally `REDIS_URL` in `.env` (see `.env.example`). Without Redis, Django uses local memory cache and database-backed sessions.

## Heavy media / object storage

Install `django-storages` and `boto3`, then enable `USE_S3=true` and related AWS env vars in `.env` (wired in `mtms/settings.py`).

## Translations (uz / ru / en)

UI strings use Django i18n (`gettext_lazy` in Python/models; `{% trans %}` in templates).

```powershell
python manage.py makemessages -l uz -l ru -l en
python manage.py compilemessages
```

(`gettext` tools must be installed for `makemessages` on Windows.)

Language switching uses Django’s cookie-based `/i18n/setlang/` flow via small POST forms in `templates/base.html`.
