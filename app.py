import os
import re
import redis
import smtplib
import secrets
import logging
from email_validator import validate_email, EmailNotValidError
from email.message import EmailMessage
from functools import wraps

from flask import Flask, render_template, redirect, url_for, request, flash, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

# ── Logging ─────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Environment Variables ────────────────────────────────────────────────────────
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM")

REDIS_SERVER_NUMBER = os.getenv("REDIS_SERVER_NUMBER", "127.0.0.1")
REDIS_PORT_NUMBER   = int(os.getenv("REDIS_PORT_NUMBER", "6379"))
REDIS_PASSWORD      = os.getenv("REDIS_PASSWORD")

ADMIN_USR = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_KEY = os.getenv("ADMIN_PASSWORD")

# ── Startup warnings ─────────────────────────────────────────────────────────────
if not EMAIL_USER:
    logger.warning("EMAIL_USER not set – email / OTP features will not work.")
if not ADMIN_KEY:
    logger.warning("ADMIN_PASSWORD not set in environment.")

_secret = os.getenv("SECRET_KEY")
if not _secret:
    logger.warning("SECRET_KEY not set in .env – sessions will be reset on every server restart!")
    _secret = os.urandom(24).hex()

# ── Redis (with in-memory fallback) ────────────────────────────────────────────────
redis_client = redis.Redis(
    host=REDIS_SERVER_NUMBER,
    port=REDIS_PORT_NUMBER,
    password=REDIS_PASSWORD,
    decode_responses=True
)
# We will use this dictionary to store OTPs if Redis is not running globally
FALLBACK_OTP_STORE = {}

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", secrets.token_hex(24)),
    SQLALCHEMY_DATABASE_URI="sqlite:///data.db",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAX_CONTENT_LENGTH=10 * 1024 * 1024
)

UPLOAD_FOLDER      = "uploads"
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

db      = SQLAlchemy(app)
csrf    = CSRFProtect(app)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://"
)

# ── Email validation ─────────────────────────────────────────────────────────────
def is_valid_email(email):
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False

# ── Models ───────────────────────────────────────────────────────────────────────
class Link(db.Model):
    id    = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    url   = db.Column(db.String(300), nullable=False)

class FileUpload(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    title    = db.Column(db.String(120), nullable=False)
    filename = db.Column(db.String(300), nullable=False)

class Collaborator(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(120), nullable=False)
    email        = db.Column(db.String(120), nullable=False)
    resume_url   = db.Column(db.String(300), nullable=False)
    contribution = db.Column(db.String(300), nullable=False)

# ── Helpers ──────────────────────────────────────────────────────────────────────
def allowed_file(filename):
    """Return True only if filename is non-empty and has an allowed extension."""
    if not filename or filename.strip() == "":
        return False
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Admin access only", "danger")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

# ── Home ─────────────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return redirect(url_for("resources"))

# ── Admin Auth ───────────────────────────────────────────────────────────────────
@app.route("/admin-entry")
def admin_entry():
    if session.get("is_admin"):
        session.pop("is_admin")
        flash("Logged out", "info")
        return redirect(url_for("resources"))
    return redirect(url_for("admin_login"))

@app.route("/admin-login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def admin_login():
    if session.get("is_admin"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        if (request.form["username"] == ADMIN_USR and
                request.form["password"] == ADMIN_KEY):
            session["is_admin"] = True
            flash("Login successful", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid credentials", "danger")
    return render_template("admin_login.html")

@app.route("/admin-logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("Logged out", "info")
    return redirect(url_for("resources"))

# ── Public Resources ─────────────────────────────────────────────────────────────
@app.route("/resources")
def resources():
    links = Link.query.all()
    files = FileUpload.query.all()
    return render_template("resources.html", links=links, files=files)

# ── Dashboard ────────────────────────────────────────────────────────────────────
@app.route("/dashboard")
@admin_required
def dashboard():
    links  = Link.query.all()
    files  = FileUpload.query.all()
    people = Collaborator.query.all()
    return render_template("dashboard.html", links=links, files=files, people=people)

# ── Links ────────────────────────────────────────────────────────────────────────
@app.route("/add-link", methods=["GET", "POST"])
@admin_required
def add_link():
    if request.method == "POST":
        db.session.add(Link(
            title=request.form["title"],
            url=request.form["url"]
        ))
        db.session.commit()
        flash("Link added", "success")
        return redirect(url_for("dashboard"))
    return render_template("add_link.html")

@app.route("/edit-link/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_link(id):
    link = Link.query.get_or_404(id)
    if request.method == "POST":
        link.title = request.form["title"]
        link.url   = request.form["url"]
        db.session.commit()
        flash("Link updated", "success")
        return redirect(url_for("dashboard"))
    return render_template("edit_link.html", link=link)

@app.route("/delete-link/<int:id>", methods=["POST"])
@admin_required
def delete_link(id):
    link = Link.query.get_or_404(id)
    db.session.delete(link)
    db.session.commit()
    flash("Link deleted", "success")
    return redirect(url_for("dashboard"))

# ── Files ────────────────────────────────────────────────────────────────────────
@app.route("/add-file", methods=["GET", "POST"])
@admin_required
def add_file():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("No file selected.", "danger")
            return redirect(url_for("add_file"))
        if not allowed_file(file.filename):
            flash("Invalid file type. Allowed: txt, pdf, png, jpg, jpeg, gif", "danger")
            return redirect(url_for("add_file"))
        filename = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        db.session.add(FileUpload(title=request.form["title"], filename=filename))
        db.session.commit()
        flash("File uploaded", "success")
        return redirect(url_for("dashboard"))
    return render_template("add_file.html")

@app.route("/edit-file/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_file(id):
    file = FileUpload.query.get_or_404(id)
    if request.method == "POST":
        file.title = request.form["title"]
        db.session.commit()
        flash("File updated", "success")
        return redirect(url_for("dashboard"))
    return render_template("edit_file.html", file=file)

@app.route("/download/<int:id>")
def download(id):
    f = FileUpload.query.get_or_404(id)
    return send_from_directory(UPLOAD_FOLDER, f.filename, as_attachment=True)

@app.route("/preview/<int:id>")
def preview_file(id):
    file = FileUpload.query.get_or_404(id)
    return send_from_directory(app.config["UPLOAD_FOLDER"], file.filename, as_attachment=False)

@app.route("/delete-file/<int:id>", methods=["POST"])
@admin_required
def delete_file(id):
    f    = FileUpload.query.get_or_404(id)
    path = os.path.join(UPLOAD_FOLDER, f.filename)
    if os.path.exists(path):
        os.remove(path)
    db.session.delete(f)
    db.session.commit()
    flash("File deleted", "success")
    return redirect(url_for("dashboard"))

# ── Collaborators ─────────────────────────────────────────────────────────────────
@app.route("/collaborators")
def collaborators():
    people = Collaborator.query.all()
    return render_template("collaborators.html", people=people)

@app.route("/add-collaborator", methods=["GET", "POST"])
@admin_required
def add_collaborator():
    if request.method == "POST":
        db.session.add(Collaborator(
            name=request.form["name"],
            email=request.form["email"],
            resume_url=request.form["resume"],
            contribution=request.form["contribution"]
        ))
        db.session.commit()
        flash("Collaborator added", "success")
        return redirect(url_for("collaborators"))
    return render_template("add_collaborator.html")

@app.route("/edit-collaborator/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_collaborator(id):
    c = Collaborator.query.get_or_404(id)
    if request.method == "POST":
        c.name         = request.form["name"]
        c.email        = request.form["email"]
        c.resume_url   = request.form["resume"]
        c.contribution = request.form["contribution"]
        db.session.commit()
        flash("Collaborator updated", "success")
        return redirect(url_for("collaborators"))
    return render_template("edit_collaborator.html", collaborator=c)

@app.route("/delete-collaborator/<int:id>", methods=["POST"])
@admin_required
def delete_collaborator(id):
    c = Collaborator.query.get_or_404(id)
    db.session.delete(c)
    db.session.commit()
    flash("Collaborator deleted", "success")
    return redirect(url_for("dashboard"))

# ── Email & OTP Helpers ───────────────────────────────────────────────────────────
def send_email(to, otp):
    msg = EmailMessage()
    msg["From"]    = EMAIL_FROM
    msg["To"]      = to
    msg["Subject"] = "Eknal Technologies – Email Verification Code"
    msg.add_alternative(f"""
<html>
<body style="background-color:#f4f6fb; font-family: Arial, sans-serif; padding:30px;">
  <div style="max-width:480px;margin:auto;background:#ffffff;border-radius:12px;
              padding:30px;box-shadow:0 4px 12px rgba(0,0,0,0.08);text-align:center;">
    <img src="https://i.ibb.co/39ZNH1W0/eknal-link.png"
         style="height:50px;margin-bottom:20px;" alt="Eknal Link Logo"/>
    <h2 style="color:#4f46e5; margin-bottom:10px;">OTP Verification</h2>
    <p style="color:#555; font-size:15px;">
      We received a request to update your collaborator profile.
    </p>
    <p style="color:#555; font-size:15px;">Use the verification code below:</p>
    <div style="font-size:28px;font-weight:bold;letter-spacing:6px;background:#f0f2ff;
                padding:15px;border-radius:8px;margin:20px 0;color:#111;">{otp}</div>
    <p style="color:#777; font-size:14px;">This code is valid for 5 minutes.</p>
    <p style="color:#999; font-size:13px;">
      If you did not request this, you can safely ignore this email.
    </p>
    <hr style="border:none;border-top:1px solid #eee;margin:25px 0;">
    <p style="font-size:13px;color:#666;">© Eknal Technologies</p>
  </div>
</body>
</html>
""", subtype="html")
    if not EMAIL_USER or EMAIL_USER == "your-email@yourdomain.com":
        raise ValueError("Email credentials not configured in .env file")
        
    with smtplib.SMTP("smtp.zoho.in", 587) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

def generate_otp():
    """Generate a cryptographically secure 6-digit OTP."""
    return "".join([str(secrets.randbelow(10)) for _ in range(6)])

def save_otp(email, otp):
    try:
        redis_client.ping()
        redis_client.setex(f"otp:{email}", 300, otp)
    except Exception:
        logger.warning("Redis not available, using memory store for OTP.")
        FALLBACK_OTP_STORE[email] = otp

def get_redis_otp(email):
    try:
        redis_client.ping()
        return redis_client.get(f"otp:{email}")
    except Exception:
        return FALLBACK_OTP_STORE.get(email)

def del_redis_otp(email):
    try:
        redis_client.ping()
        redis_client.delete(f"otp:{email}")
    except Exception:
        FALLBACK_OTP_STORE.pop(email, None)

# ── OTP Routes ────────────────────────────────────────────────────────────────────
@app.route("/request-edit", methods=["GET", "POST"])
@limiter.limit("100 per 10 minutes")
def request_edit():
    if request.method == "POST":
        email = request.form["email"].strip()

        if not email:
            flash("Please enter your email address.", "danger")
            return redirect(url_for("request_edit"))

        if not is_valid_email(email):
            flash("Please enter a valid email address.", "danger")
            return redirect(url_for("request_edit"))

        collaborator = Collaborator.query.filter_by(email=email).first()
        if not collaborator:
            flash("Email not found in our records.", "danger")
            return redirect(url_for("request_edit"))

        try:
            otp = generate_otp()
            save_otp(email, otp)
            send_email(email, otp)
        except Exception:
            flash("Could not send OTP. Please try again later.", "danger")
            return redirect(url_for("request_edit"))

        session["otp_email"] = email
        flash("Verification code sent to your email.", "success")
        return redirect(url_for("verify_otp"))

    return render_template("request_edit.html")

@app.route("/resend-otp", methods=["POST"])
@limiter.limit("100 per 10 minutes")
def resend_otp():
    email = session.get("otp_email")
    if not email:
        flash("Session expired. Please start again.", "danger")
        return redirect(url_for("request_edit"))
    collaborator = Collaborator.query.filter_by(email=email).first()
    if not collaborator:
        flash("Email not found.", "danger")
        return redirect(url_for("request_edit"))
    try:
        otp = generate_otp()
        save_otp(email, otp)
        send_email(email, otp)
    except Exception as e:
        logger.error(f"Error resending OTP: {e}")
        flash("Could not send OTP. Please check email credentials in .env.", "danger")
        return redirect(url_for("verify_otp"))
    
    flash("A new OTP has been sent to your email.", "success")
    return redirect(url_for("verify_otp"))

@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if request.method == "POST":
        user_otp  = request.form["otp"]
        email     = session.get("otp_email")
        if not email:
            flash("Session expired.", "danger")
            return redirect(url_for("request_edit"))
        saved_otp = get_redis_otp(email)
        if saved_otp is None:
            flash("OTP expired or service unavailable. Please request a new one.", "danger")
            return redirect(url_for("request_edit"))
        if user_otp == saved_otp:
            del_redis_otp(email)
            session["verified_email"] = email
            flash("OTP verified successfully.", "success")
            return redirect(url_for("self_edit_collaborator"))
        flash("Incorrect OTP. Please try again.", "danger")
    return render_template("verify_otp.html")

@app.route("/self-edit", methods=["GET", "POST"])
def self_edit_collaborator():
    email = session.get("verified_email")
    if not email:
        flash("Unauthorized access.", "danger")
        return redirect(url_for("request_edit"))
    collaborator = Collaborator.query.filter_by(email=email).first_or_404()
    if request.method == "POST":
        collaborator.name         = request.form["name"]
        collaborator.resume_url   = request.form["resume"]
        collaborator.contribution = request.form["contribution"]
        db.session.commit()
        session.pop("verified_email")
        session.pop("otp_email", None)
        flash("Your profile has been updated successfully.", "success")
        return redirect(url_for("collaborators"))
    return render_template("self_edit.html", collaborator=collaborator)

# ── Error Handlers ────────────────────────────────────────────────────────────────
@app.errorhandler(413)
def file_too_large(e):
    flash("File is too large. Maximum allowed size is 10 MB.", "danger")
    return redirect(url_for("add_file"))

@app.errorhandler(429)
def too_many_requests(e):
    flash("Too many requests. Please wait a few minutes and try again.", "danger")
    return redirect(url_for("request_edit"))

@app.errorhandler(400)
def csrf_error(e):
    # This catches CSRF token missing/expired errors
    flash("Your session has expired or the request was invalid. Please try again.", "warning")
    return redirect(request.referrer or url_for("resources"))

# ── Run ───────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    # Explicitly set to False for Quality Gate; user can set to True in .env if needed
    app.run(debug=False)
