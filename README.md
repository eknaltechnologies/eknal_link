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
python -m venv .venv or python -m venv <your_env_name>
.venv\Scripts\activate
```

Install the dependencies:

```powershell
pip install -r requirements.txt
```

## Database Setup

After cloning the repo and installing dependencies, initialize and migrate the database:

Windows CMD:
```cmd
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

This will create the SQLite database at `instance/data.db` with all required tables.

Create a `.env` file in the project root with these values:

```env
SECRET_KEY=your_secret_key
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_admin_password
REDIS_SERVER_NUMBER=redis_host
REDIS_PORT_NUMBER=redis_port
REDIS_PASSWORD=your_redis_password
EMAIL_USER=email_user
EMAIL_PASS=email_password
EMAIL_FROM=your_from_email
EMAIL_HOST= your_email_host
EMAIL_PORT=your_email_port
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
- To reset the database, delete `instance/data.db` and run `flask db upgrade` again
- For making schema changes, use `flask db migrate -m "description"` followed by `flask db upgrade`
