# Saving Grace – Backend

Django REST API for [Saving Grace Animals for Adoption](https://savinggracenc.org), a dog shelter in Wake Forest, NC.

This repo is one half of a two-repo project. The other half is the React frontend at `https://github.com/sleif9777/Sheltercenter-frontend.git`. See the parent workspace's `CLAUDE.md` for cross-repo context.

**GitHub remote:** `https://github.com/sleif9777/Sheltercenter-backend.git`
**Heroku remote:** `https://git.heroku.com/sheltercenter-backend.git`

---

## Commit Convention

Use **Conventional Commits**: `<type>(<optional scope>): <short description>`

| Type | When to use |
|---|---|
| `feat` | New feature or user-visible behavior |
| `fix` | Bug fix |
| `refactor` | Code restructuring with no behavior change |
| `style` | Formatting, whitespace, no logic change |
| `chore` | Maintenance (deps, config, migrations) |
| `docs` | Documentation only |
| `perf` | Performance improvement |
| `test` | Adding or fixing tests |

Examples:
```
feat(dogs): add coat color field to dog model
fix(appointments): prevent double-booking on concurrent requests
chore(deps): bump django to 5.1.5
```

---

## Setup

The `venv/` must live alongside `manage.py` in this directory for `runserver` to work correctly.

```bash
source venv/bin/activate
pip install -r requirements.txt   # if reinstalling
```

### Environment Variables

Create `.env` in this directory:

```properties
DEBUG=1
SECRET_KEY="your-secret-key"

# Email (Mailgun)
EMAIL_HOST="smtp.mailgun.com"
EMAIL_USER="adoptions@mg.savinggracenc.org"
EMAIL_PASSWORD="..."
MAILGUN_API_KEY="..."
MAILGUN_SENDER="Saving Grace Animals for Adoption <adoptions@mg.savinggracenc.org>"
MAILGUN_SENDER_DOMAIN="mg.savinggracenc.org"

# Shelterluv API
SHELTERLUV_API_KEY="..."

# PostgreSQL (omit all to use SQLite locally)
POSTGRES_DB="..."
POSTGRES_USER="..."
POSTGRES_PASSWORD="..."
POSTGRES_HOST="..."
POSTGRES_PORT="5432"
```

If no `POSTGRES_*` vars are set, the app uses `db.sqlite3` — sufficient for local development.

---

## Running Locally

```bash
source venv/bin/activate
python manage.py runserver         # dev server with auto-reload at http://localhost:8000
# OR
gunicorn backend.wsgi              # production-style
```

---

## Migrations

```bash
source venv/bin/activate
python manage.py migrate
python manage.py makemigrations <app_name>   # after model changes
```

---

## Management Commands

```bash
# Sync dog records from the Shelterluv API
python manage.py import_dogs
python manage.py import_dogs --dog-id <id>   # test against a single dog

# Send day-prior appointment reminder emails
python manage.py run_reminders
```

---

## Code Style

Configured in `pyproject.toml`:

- **Black** — line length 100, targets Python 3.10
- **isort** — Black-compatible profile, line length 100
- **mypy** — strict (`disallow_untyped_defs`, `disallow_incomplete_defs`); excludes `migrations/`
- **flake8** — see `.flake8`

---

## Stack

- Django 5.1 + Django REST Framework 3.15
- JWT auth via `djangorestframework-simplejwt` (15-minute access tokens)
- Email via Mailgun (`django-anymail`)
- PostgreSQL (prod) / SQLite (local)
- Heroku deployment via `django-on-heroku` + Gunicorn
- Shelterluv API integration (dog sync)
- Pandas + OpenPyXL for Excel-based adopter imports

---

## Django Apps

| App | Purpose |
|---|---|
| `users` | Authentication; `UserProfile` is the custom user model |
| `adopters` | Adopter profiles and management |
| `dogs` | Dog records; synced from Shelterluv API via `import_dogs` |
| `appointments` | Appointment slots (admin-created) |
| `appointment_bases` | Recurring appointment slot templates |
| `admin_appointments` | Admin-facing appointment views |
| `admin_appointment_bases` | Admin-facing template views |
| `bookings` | Adopter bookings against appointment slots |
| `pending_adoptions` | Adoptions currently in progress |
| `pending_adoption_updates` | Change history for pending adoptions |
| `watchlist_entries` | Adopter watchlists for specific dogs |
| `email_templates` | Email content definitions and sending logic |
| `closed_dates` | Dates when scheduling is blocked |
| `open_house_appointments` | Open house event scheduling |
| `announcements` | Shelter-wide announcements |
| `litters` | Dog litter records |
| `short_notice_notifications` | Notifications for last-minute appointment openings |
| `environment_settings` | Global runtime configuration flags |

---

## API Routes

Base URL: `http://localhost:8000/`

| Prefix | Resource |
|---|---|
| `Adopters/` | Adopter CRUD |
| `Appointments/` | Appointment CRUD |
| `ClosedDates/` | Closed date CRUD |
| `Dogs/` | Dog records |
| `PendingAdoptions/` | Pending adoption CRUD |
| `TemplateAppointments/` | Appointment base templates |
| `UserProfiles/` | User profile CRUD |
| `auth/token/` | JWT obtain |
| `auth/token/refresh/` | JWT refresh |
| `auth/token/verify/` | JWT verify |
