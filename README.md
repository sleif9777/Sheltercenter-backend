# Saving Grace – Backend

Django REST API backend for [Saving Grace Animals for Adoption](https://savinggracenc.org), a dog shelter in Wake Forest, NC. Powers the shelter's appointment scheduling, watchlists, messaging, check-in/check-out, and pending adoptions. Also hosts email template content and background services for appointment reminders, Shelterluv dog imports, and adopter imports from Excel.

---

## Tech Stack

- **Language:** Python
- **Framework:** Django + Django REST Framework
- **Auth:** JWT via `djangorestframework-simplejwt`
- **Email:** Mailgun via `django-anymail`
- **Deployment:** Heroku (via `django-on-heroku`)

---

## Getting Started

### Prerequisites

- Python 3.x
- pip

### Installation

```bash
git clone <repo-url>
cd sheltercenter-backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root. Required variables:

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

# PostgreSQL (optional — omit to use SQLite locally)
POSTGRES_DB="your-db-name"
POSTGRES_USER="your-db-user"
POSTGRES_PASSWORD="your-db-password"
POSTGRES_HOST="your-db-host"
POSTGRES_PORT="5432"
```

> **Database:** If the `POSTGRES_*` variables are not set, the app falls back to a local SQLite database (`db.sqlite3`), which is sufficient for local development.

### Database Setup

Apply all migrations:

```bash
cd backend
python manage.py migrate
```

### Running Locally

```bash
cd backend
gunicorn backend.wsgi
```

The API will be available at `http://localhost:8000` by default.

---

## Background Services

| Service | Description |
|---|---|
| Appointment reminders | Sends day-prior email reminders to adopters |
| Shelterluv import | Syncs dog records from the Shelterluv API |
| Adopter import | Imports adopter records from an Excel file |
