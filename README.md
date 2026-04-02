# Eknal Link

Eknal Link is a Flask application for managing resources, uploaded files, contribution types, and collaborator profiles.

## Requirements

- Python 3.10 or newer
- A virtual environment is recommended
- Redis is required for the OTP edit flow
- SMTP credentials are required for sending OTP emails

## Setup

From the project root, create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

Install the dependencies:

```powershell
pip install -r requirements.txt
```

Create a `.env` file in the project root with these values:

```env
SECRET_KEY=your-secret-key
ADMIN_USERNAME=your-admin-username
ADMIN_PASSWORD=your-admin-password
REDIS_SERVER_NUMBER=localhost
REDIS_PORT_NUMBER=6379
REDIS_PASSWORD=
EMAIL_USER=your-email@example.com
EMAIL_PASS=your-email-password
EMAIL_FROM=your-email@example.com
```

## Start the server

Run the Flask app:

```powershell
python app.py
```

The app runs at:

```text
http://127.0.0.1:9123
```

On first start, the app automatically creates the `instance` folder and the SQLite tables if they do not already exist.

## Notes

- Public resources are available at `/resources`
- Admin login is available at `/admin-login`
- The self-edit OTP flow requires Redis and valid email settings
- If you delete `instance/data.db`, restart the app to recreate the database
