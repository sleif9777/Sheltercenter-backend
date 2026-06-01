# Saving Grace – Backend

Django REST API for [Saving Grace Animals for Adoption](https://savinggracenc.org), a dog shelter in Wake Forest, NC. Powers appointment scheduling, adopter management, watchlists, check-in/check-out, pending adoptions, email notifications, and Shelterluv dog sync.

---

## Tech Stack

- **Language:** Python 3
- **Framework:** Django 5.1 + Django REST Framework 3.15
- **Auth:** JWT via `djangorestframework-simplejwt` (15-minute access tokens)
- **Email:** Mailgun via `django-anymail`
- **Database:** PostgreSQL (production) · SQLite (local development)
- **Deployment:** Heroku via `django-on-heroku` + Gunicorn

---

## Getting Started

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
git clone https://github.com/sleif9777/Sheltercenter-backend.git
cd Sheltercenter-backend

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in this directory:

```properties
DEBUG=1
SECRET_KEY="your-secret-key"

# Email (Mailgun)
EMAIL_HOST="smtp.mailgun.com"
EMAIL_USER="adoptions@mg.savinggracenc.org"
EMAIL_PASSWORD="your-email-password"
MAILGUN_API_KEY="your-mailgun-api-key"
MAILGUN_SENDER="Saving Grace Animals for Adoption <adoptions@mg.savinggracenc.org>"
MAILGUN_SENDER_DOMAIN="mg.savinggracenc.org"

# Shelterluv integration
SHELTERLUV_API_KEY="your-shelterluv-api-key"

# PostgreSQL (omit all four to use SQLite locally)
POSTGRES_DB="your-db-name"
POSTGRES_USER="your-db-user"
POSTGRES_PASSWORD="your-db-password"
POSTGRES_HOST="your-db-host"
POSTGRES_PORT="5432"
```

### Database Setup

```bash
python manage.py migrate
```

### Running Locally

```bash
source venv/bin/activate
python manage.py runserver      # dev server with auto-reload at http://localhost:8000
```

---

## Background Services

| Command | Description |
|---|---|
| `python manage.py import_dogs` | Syncs publishable dog records from the Shelterluv API; safely deactivates dogs no longer listed |
| `python manage.py run_reminders` | Sends day-prior appointment reminder emails to all booked adopters |

---

## API Overview

Base URL: `http://localhost:8000/`

| Endpoint | Resource |
|---|---|
| `Adopters/` | Adopter profiles |
| `Appointments/` | Appointment slots |
| `ClosedDates/` | Blocked scheduling dates |
| `Dogs/` | Dog records |
| `PendingAdoptions/` | In-progress adoptions |
| `TemplateAppointments/` | Recurring slot templates |
| `UserProfiles/` | User accounts |
| `auth/token/` | Obtain JWT |
| `auth/token/refresh/` | Refresh JWT |

---

## Code Style

```bash
black .         # format (line length 100)
isort .         # sort imports
mypy .          # type check
```

Configuration in `pyproject.toml`. Migrations are excluded from type checking.

---

## Contributing

Commits must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(dogs): add coat color field
fix(appointments): prevent double-booking on concurrent requests
chore: bump django to 5.2
```
