import os
import logging
import secrets
from flask import Flask, render_template, redirect, url_for, request, flash, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from werkzeug.utils import secure_filename
from functools import wraps
from dotenv import load_dotenv
import redis
import smtplib
from email.message import EmailMessage
import random
import re
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# Configure logging for better debugging and monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables with validation
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS") 
EMAIL_FROM = os.getenv("EMAIL_FROM")

REDIS_SERVER_NUMBER = os.getenv("REDIS_SERVER_NUMBER", "localhost")
REDIS_PORT_NUMBER = int(os.getenv("REDIS_PORT_NUMBER", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

# Validate critical environment variables
if not all([EMAIL_USER, EMAIL_PASS, EMAIL_FROM]):
    logger.warning("Email configuration incomplete. OTP functionality will not work.")

# Initialize Redis client with error handling
try:
    redis_client = redis.Redis(
        host=REDIS_SERVER_NUMBER,
        port=REDIS_PORT_NUMBER,
        password=REDIS_PASSWORD if REDIS_PASSWORD else None,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    # Test Redis connection
    redis_client.ping()
    logger.info("Redis connection established successfully")
except redis.ConnectionError:
    logger.error("Failed to connect to Redis. OTP functionality will not work.")
    redis_client = None
# ---------------- APP CONFIGURATION ----------------
app = Flask(__name__)

# Security improvements: Use environment variables for sensitive config
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///data.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# File upload configuration with security limits
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))  # 16MB default
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif", "doc", "docx"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# Create upload directory if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    logger.info(f"Created upload directory: {UPLOAD_FOLDER}")

db = SQLAlchemy(app)

# Admin credentials from environment variables (more secure)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Warn if default credentials are being used
if ADMIN_USERNAME == "admin" and ADMIN_PASSWORD == "admin123":
    logger.warning("Using default admin credentials! Change ADMIN_USERNAME and ADMIN_PASSWORD in production.")

# ---------------- CONSTANTS ----------------
# Template names to avoid duplication
TEMPLATE_ADD_LINK = "add_link.html"
TEMPLATE_EDIT_LINK = "edit_link.html"
TEMPLATE_ADD_FILE = "add_file.html"
TEMPLATE_ADD_COLLABORATOR = "add_collaborator.html"
TEMPLATE_EDIT_COLLABORATOR = "edit_collaborator.html"
TEMPLATE_REQUEST_EDIT = "request_edit.html"
TEMPLATE_SELF_EDIT = "self_edit.html"

# URL schemes - Security: Only allow HTTPS for better security
HTTPS_SCHEME = 'https://'
VALID_SCHEMES = (HTTPS_SCHEME,)  # Only HTTPS allowed for security

# Error messages to avoid duplication
ERROR_UNEXPECTED = "Unexpected error occurred. Please try again."

# ---------------- DATABASE MODELS ----------------
class Link(db.Model):
    """Model for storing resource links with validation"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    url = db.Column(db.String(500), nullable=False)  # Increased length for longer URLs
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    def __repr__(self):
        return f'<Link {self.title}>'

class FileUpload(db.Model):
    """Model for storing uploaded file information"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    filename = db.Column(db.String(300), nullable=False)
    original_filename = db.Column(db.String(300), nullable=False)  # Store original name
    file_size = db.Column(db.Integer)  # Store file size in bytes
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    def __repr__(self):
        return f'<FileUpload {self.title}>'

class Collaborator(db.Model):
    """Model for storing collaborator information with validation"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)  # Ensure unique emails
    resume_url = db.Column(db.String(500), nullable=False)
    contribution = db.Column(db.Text, nullable=False)  # Use Text for longer descriptions
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    def __repr__(self):
        return f'<Collaborator {self.name}>'

# ---------------- HELPER FUNCTIONS ----------------
def allowed_file(filename):
    """Check if uploaded file has an allowed extension"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_email(email):
    """Basic email validation using regex"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_url(url):
    """Validate URL format and ensure it uses HTTPS for security"""
    try:
        result = urlparse(url)
        # Security: Only allow HTTPS URLs
        return result.scheme == 'https' and result.netloc
    except (ValueError, TypeError, AttributeError):
        return False

def sanitize_input(text, max_length=None):
    """Basic input sanitization - strip whitespace and limit length"""
    if not text:
        return ""
    text = text.strip()
    if max_length and len(text) > max_length:
        text = text[:max_length]
    return text

def admin_required(f):
    """Decorator to require admin authentication for routes"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Admin access required. Please log in.", "danger")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

# ---------------- HOME ----------------
@app.route("/")
def home():
    return redirect(url_for("resources"))

# ---------------- ADMIN AUTH ----------------
@app.route("/admin-entry")
def admin_entry():
    if session.get("is_admin"):
        session.pop("is_admin")
        flash("Logged out", "info")
        return redirect(url_for("resources"))
    else:
        return redirect(url_for("admin_login"))
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    """Admin login with improved security"""
    if session.get("is_admin"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = sanitize_input(request.form.get("username", ""))
        password = request.form.get("password", "")
        
        # Basic rate limiting - check if too many failed attempts
        failed_attempts = session.get("failed_login_attempts", 0)
        if failed_attempts >= 5:
            flash("Too many failed attempts. Please try again later.", "danger")
            return render_template("admin_login.html")
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["is_admin"] = True
            session.pop("failed_login_attempts", None)  # Reset failed attempts
            session.permanent = True  # Make session persistent
            flash("Login successful! Welcome to the admin dashboard.", "success")
            logger.info(f"Admin login successful from IP: {request.remote_addr}")
            return redirect(url_for("dashboard"))
        else:
            # Increment failed attempts
            session["failed_login_attempts"] = failed_attempts + 1
            flash("Invalid credentials. Please check your username and password.", "danger")
            logger.warning(f"Failed admin login attempt from IP: {request.remote_addr}")

    return render_template("admin_login.html")

@app.route("/admin-logout")
def admin_logout():
    """Admin logout with session cleanup"""
    session.pop("is_admin", None)
    session.pop("failed_login_attempts", None)
    flash("Successfully logged out.", "info")
    logger.info("Admin logged out")
    return redirect(url_for("resources"))

# ---------------- PUBLIC RESOURCES ----------------
@app.route("/resources")
def resources():
    links = Link.query.all()
    files = FileUpload.query.all()
    return render_template("resources.html", links=links, files=files)

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
@admin_required
def dashboard():
    links = Link.query.all()
    files = FileUpload.query.all()
    return render_template("dashboard.html", links=links, files=files)

# ---------------- LINKS ----------------
@app.route("/add-link", methods=["GET","POST"])
@admin_required
def add_link():
    """Add a new resource link with validation"""
    if request.method == "POST":
        title = sanitize_input(request.form.get("title", ""), 120)
        url = sanitize_input(request.form.get("url", ""), 500)
        
        # Validate inputs
        if not title:
            flash("Please provide a title for the link.", "danger")
            return render_template(TEMPLATE_ADD_LINK)
            
        if not url:
            flash("Please provide a valid URL.", "danger")
            return render_template(TEMPLATE_ADD_LINK)
            
        # Add http:// if no scheme is provided
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        if not validate_url(url):
            flash("Please provide a valid URL format.", "danger")
            return render_template("add_link.html")
        
        try:
            new_link = Link(title=title, url=url)
            db.session.add(new_link)
            db.session.commit()
            flash(f"Link '{title}' added successfully!", "success")
            logger.info(f"New link added: {title}")
            return redirect(url_for("dashboard"))
        except (SQLAlchemyError, IntegrityError) as e:
            db.session.rollback()
            flash("Error adding link. Please try again.", "danger")
            logger.error(f"Database error adding link: {str(e)}")
        except (OSError, IOError) as e:
            db.session.rollback()
            flash(ERROR_UNEXPECTED, "danger")
            logger.error(f"System error adding link: {str(e)}")
            
    return render_template(TEMPLATE_ADD_LINK)

@app.route("/edit-link/<int:id>", methods=["GET","POST"])
@admin_required
def edit_link(id):
    """Edit an existing link with validation"""
    link = Link.query.get_or_404(id)

    if request.method == "POST":
        title = sanitize_input(request.form.get("title", ""), 120)
        url = sanitize_input(request.form.get("url", ""), 500)
        
        # Validate inputs
        if not title:
            flash("Please provide a title for the link.", "danger")
            return render_template(TEMPLATE_EDIT_LINK, link=link)
            
        if not url:
            flash("Please provide a valid URL.", "danger")
            return render_template(TEMPLATE_EDIT_LINK, link=link)
            
        # Add https:// if no scheme is provided (security: always use HTTPS)
        if not url.startswith(VALID_SCHEMES):
            url = HTTPS_SCHEME + url
            
        if not validate_url(url):
            flash("Please provide a valid URL format.", "danger")
            return render_template(TEMPLATE_EDIT_LINK, link=link)
        
        try:
            link.title = title
            link.url = url
            db.session.commit()
            flash(f"Link '{title}' updated successfully!", "success")
            logger.info(f"Link updated: {title}")
            return redirect(url_for("dashboard"))
        except (SQLAlchemyError, IntegrityError) as e:
            db.session.rollback()
            flash("Error updating link. Please try again.", "danger")
            logger.error(f"Database error updating link: {str(e)}")
        except (OSError, IOError) as e:
            db.session.rollback()
            flash(ERROR_UNEXPECTED, "danger")
            logger.error(f"System error updating link: {str(e)}")

    return render_template(TEMPLATE_EDIT_LINK, link=link)

@app.route("/delete-link/<int:id>", methods=["POST"])
@admin_required
def delete_link(id):
    """Delete a link with proper error handling"""
    try:
        link = Link.query.get_or_404(id)
        link_title = link.title  # Store title for logging
        db.session.delete(link)
        db.session.commit()
        flash(f"Link '{link_title}' deleted successfully.", "success")
        logger.info(f"Link deleted: {link_title}")
    except (SQLAlchemyError, IntegrityError) as e:
        db.session.rollback()
        flash("Error deleting link. Please try again.", "danger")
        logger.error(f"Database error deleting link: {str(e)}")
    except (OSError, IOError) as e:
        db.session.rollback()
        flash(ERROR_UNEXPECTED, "danger")
        logger.error(f"System error deleting link: {str(e)}")
    
    return redirect(url_for("dashboard"))

# ---------------- FILES ----------------
def validate_file_upload(file):
    """Validate uploaded file and return validation result"""
    if not file.filename:
        return False, "No file selected. Please choose a file to upload."
    
    if not allowed_file(file.filename):
        return False, f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
    
    return True, None

def generate_unique_filename(original_filename):
    """Generate a unique filename to prevent overwrites"""
    filename = secure_filename(original_filename)
    counter = 1
    base_name, extension = os.path.splitext(filename)
    
    while os.path.exists(os.path.join(UPLOAD_FOLDER, filename)):
        filename = f"{base_name}_{counter}{extension}"
        counter += 1
    
    return filename

@app.route("/add-file", methods=["GET","POST"])
@admin_required
def add_file():
    """Add a new file with enhanced security and validation"""
    if request.method == "POST":
        title = sanitize_input(request.form.get("title", ""), 120)
        
        if not title:
            flash("Please provide a title for the file.", "danger")
            return render_template(TEMPLATE_ADD_FILE)
        
        # Check if file was uploaded
        if 'file' not in request.files:
            flash("No file selected. Please choose a file to upload.", "danger")
            return render_template(TEMPLATE_ADD_FILE)
            
        file = request.files['file']
        
        # Validate file
        is_valid, error_message = validate_file_upload(file)
        if not is_valid:
            flash(error_message, "danger")
            return render_template(TEMPLATE_ADD_FILE)

        try:
            # Generate secure filename
            original_filename = file.filename
            filename = generate_unique_filename(original_filename)
            
            # Save file
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            
            # Get file size and save to database
            file_size = os.path.getsize(file_path)
            new_file = FileUpload(
                title=title,
                filename=filename,
                original_filename=original_filename,
                file_size=file_size
            )
            db.session.add(new_file)
            db.session.commit()

            flash(f"File '{title}' uploaded successfully!", "success")
            logger.info(f"File uploaded: {title} ({filename})")
            return redirect(url_for("dashboard"))
            
        except (SQLAlchemyError, IntegrityError, OSError, IOError) as e:
            db.session.rollback()
            # Clean up file if database save failed
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            flash("Error uploading file. Please try again.", "danger")
            logger.error(f"Error uploading file: {str(e)}")

    return render_template(TEMPLATE_ADD_FILE)
@app.route("/edit-file/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_file(id):
    """Edit file metadata (title only for security)"""
    file_upload = FileUpload.query.get_or_404(id)

    if request.method == "POST":
        title = sanitize_input(request.form.get("title", ""), 120)
        
        if not title:
            flash("Please provide a title for the file.", "danger")
            return render_template("edit_file.html", file=file_upload)
        
        try:
            file_upload.title = title
            db.session.commit()
            flash(f"File '{title}' updated successfully!", "success")
            logger.info(f"File metadata updated: {title}")
            return redirect(url_for("dashboard"))
        except (SQLAlchemyError, IntegrityError) as e:
            db.session.rollback()
            flash("Error updating file. Please try again.", "danger")
            logger.error(f"Error updating file: {str(e)}")

    return render_template("edit_file.html", file=file_upload)
@app.route("/download/<int:id>")
def download(id):
    """Download file with security checks"""
    try:
        file_upload = FileUpload.query.get_or_404(id)
        file_path = os.path.join(UPLOAD_FOLDER, file_upload.filename)
        
        # Security check: ensure file exists and is within upload folder
        if not os.path.exists(file_path) or os.path.commonpath([UPLOAD_FOLDER, file_path]) != UPLOAD_FOLDER:
            flash("File not found or access denied.", "danger")
            return redirect(url_for("resources"))
            flash("File not found or access denied.", "danger")
            return redirect(url_for("resources"))
            
        logger.info(f"File downloaded: {file_upload.title}")
        return send_from_directory(
            UPLOAD_FOLDER, 
            file_upload.filename, 
            as_attachment=True,
            download_name=file_upload.original_filename  # Use original filename for download
        )
    except (OSError, IOError, FileNotFoundError) as e:
        logger.error(f"Error downloading file: {str(e)}")
        flash("Error downloading file.", "danger")
        return redirect(url_for("resources"))

@app.route("/preview/<int:id>")
def preview_file(id):
    """Preview file with security checks"""
    try:
        file_upload = FileUpload.query.get_or_404(id)
        file_path = os.path.join(UPLOAD_FOLDER, file_upload.filename)
        
        # Security check: ensure file exists and is within upload folder
        if not os.path.exists(file_path) or os.path.commonpath([UPLOAD_FOLDER, file_path]) != UPLOAD_FOLDER:
            flash("File not found or access denied.", "danger")
            return redirect(url_for("resources"))
            flash("File not found or access denied.", "danger")
            return redirect(url_for("resources"))
            
        return send_from_directory(
            app.config["UPLOAD_FOLDER"],
            file_upload.filename,
            as_attachment=False
        )
    except (OSError, IOError, FileNotFoundError) as e:
        logger.error(f"Error previewing file: {str(e)}")
        flash("Error previewing file.", "danger")
        return redirect(url_for("resources"))
@app.route("/delete-file/<int:id>", methods=["POST"])
@admin_required
def delete_file(id):
    """Delete file with proper cleanup"""
    try:
        file_upload = FileUpload.query.get_or_404(id)
        file_title = file_upload.title
        
        # Remove physical file
        file_path = os.path.join(UPLOAD_FOLDER, file_upload.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Physical file deleted: {file_upload.filename}")

        # Remove database record
        db.session.delete(file_upload)
        db.session.commit()
        
        flash(f"File '{file_title}' deleted successfully.", "success")
        logger.info(f"File deleted: {file_title}")
        
    except (SQLAlchemyError, IntegrityError, OSError, IOError) as e:
        db.session.rollback()
        flash("Error deleting file. Please try again.", "danger")
        logger.error(f"Error deleting file: {str(e)}")
    
    return redirect(url_for("dashboard"))

# ---------------- COLLABORATORS ----------------
@app.route("/collaborators")
def collaborators():
    people = Collaborator.query.all()
    return render_template("collaborators.html", people=people)

def validate_collaborator_input(name, email, resume_url, contribution):
    """Validate collaborator input data and return validation result"""
    errors = []
    
    if not name:
        errors.append("Please provide a name.")
        
    if not email or not validate_email(email):
        errors.append("Please provide a valid email address.")
        
    if not resume_url:
        errors.append("Please provide a resume URL.")
    else:
        # Add http:// if no scheme is provided for resume URL
        if not resume_url.startswith(VALID_SCHEMES):
            resume_url = HTTPS_SCHEME + resume_url
            
        if not validate_url(resume_url):
            errors.append("Please provide a valid resume URL format.")
            
    if not contribution:
        errors.append("Please provide a contribution description.")
    
    return errors, resume_url

@app.route("/add-collaborator", methods=["GET","POST"])
@admin_required
def add_collaborator():
    """Add a new collaborator with validation"""
    if request.method == "POST":
        name = sanitize_input(request.form.get("name", ""), 120)
        email = sanitize_input(request.form.get("email", ""), 120)
        resume_url = sanitize_input(request.form.get("resume", ""), 500)
        contribution = sanitize_input(request.form.get("contribution", ""), 1000)
        
        # Validate inputs
        validation_errors, validated_resume_url = validate_collaborator_input(name, email, resume_url, contribution)
        
        if validation_errors:
            for error in validation_errors:
                flash(error, "danger")
            return render_template(TEMPLATE_ADD_COLLABORATOR)
        
        # Check if email already exists
        existing_collaborator = Collaborator.query.filter_by(email=email).first()
        if existing_collaborator:
            flash("A collaborator with this email already exists.", "danger")
            return render_template(TEMPLATE_ADD_COLLABORATOR)
        
        try:
            new_collaborator = Collaborator(
                name=name,
                email=email,
                resume_url=validated_resume_url,
                contribution=contribution
            )
            db.session.add(new_collaborator)
            db.session.commit()
            flash(f"Collaborator '{name}' added successfully!", "success")
            logger.info(f"New collaborator added: {name} ({email})")
            return redirect(url_for("collaborators"))
        except (SQLAlchemyError, IntegrityError) as e:
            db.session.rollback()
            flash("Error adding collaborator. Please try again.", "danger")
            logger.error(f"Error adding collaborator: {str(e)}")

    return render_template(TEMPLATE_ADD_COLLABORATOR)

@app.route("/edit-collaborator/<int:id>", methods=["GET","POST"])
@admin_required
def edit_collaborator(id):
    """Edit an existing collaborator with validation"""
    collaborator = Collaborator.query.get_or_404(id)

    if request.method == "POST":
        name = sanitize_input(request.form.get("name", ""), 120)
        email = sanitize_input(request.form.get("email", ""), 120)
        resume_url = sanitize_input(request.form.get("resume", ""), 500)
        contribution = sanitize_input(request.form.get("contribution", ""), 1000)
        
        # Validate inputs
        validation_errors, validated_resume_url = validate_collaborator_input(name, email, resume_url, contribution)
        
        if validation_errors:
            for error in validation_errors:
                flash(error, "danger")
            return render_template(TEMPLATE_EDIT_COLLABORATOR, collaborator=collaborator)
        
        # Check if email already exists (excluding current collaborator)
        existing_collaborator = Collaborator.query.filter(
            Collaborator.email == email,
            Collaborator.id != id
        ).first()
        if existing_collaborator:
            flash("A collaborator with this email already exists.", "danger")
            return render_template(TEMPLATE_EDIT_COLLABORATOR, collaborator=collaborator)
        
        try:
            collaborator.name = name
            collaborator.email = email
            collaborator.resume_url = validated_resume_url
            collaborator.contribution = contribution
            db.session.commit()
            flash(f"Collaborator '{name}' updated successfully!", "success")
            logger.info(f"Collaborator updated: {name} ({email})")
            return redirect(url_for("collaborators"))
        except (SQLAlchemyError, IntegrityError) as e:
            db.session.rollback()
            flash("Error updating collaborator. Please try again.", "danger")
            logger.error(f"Error updating collaborator: {str(e)}")

    return render_template(TEMPLATE_EDIT_COLLABORATOR, collaborator=collaborator)

@app.route("/delete-collaborator/<int:id>", methods=["POST"])
@admin_required
def delete_collaborator(id):
    c = Collaborator.query.get_or_404(id)
    db.session.delete(c)
    db.session.commit()
    flash("Collaborator deleted", "success")
    return redirect(url_for("collaborators"))

def send_email(to, otp):
    """Send OTP email with improved error handling and security"""
    if not all([EMAIL_USER, EMAIL_PASS, EMAIL_FROM]):
        logger.error("Email configuration incomplete")
        raise Exception("Email service not configured")
    
    try:
        msg = EmailMessage()
        msg["From"] = EMAIL_FROM
        msg["To"] = to
        msg["Subject"] = "Eknal Technologies – Email Verification Code"
        
        # HTML email template with improved styling
        html_content = f"""
<html>
<body style="background-color:#f4f6fb; font-family: Arial, sans-serif; padding:30px; margin:0;">
  <div style="
    max-width:480px;
    margin:auto;
    background:#ffffff;
    border-radius:12px;
    padding:30px;
    box-shadow:0 4px 12px rgba(0,0,0,0.08);
    text-align:center;
  ">
    <!-- Logo -->
    <img src="https://i.ibb.co/39ZNH1W0/eknal-link.png"
         style="height:50px;margin-bottom:20px;"
         alt="Eknal Link Logo"/>

    <h2 style="color:#4f46e5; margin-bottom:10px; font-size:24px;">
      Email Verification
    </h2>

    <p style="color:#555; font-size:15px; line-height:1.5; margin-bottom:15px;">
      We received a request to update your collaborator profile on Eknal Link.
    </p>

    <p style="color:#555; font-size:15px; margin-bottom:20px;">
      Use the verification code below:
    </p>

    <div style="
      font-size:28px;
      font-weight:bold;
      letter-spacing:6px;
      background:#f0f2ff;
      padding:15px;
      border-radius:8px;
      margin:20px 0;
      color:#111;
      border: 2px solid #e0e7ff;
    ">
      {otp}
    </div>

    <p style="color:#777; font-size:14px; margin-bottom:15px;">
      This code is valid for 5 minutes only.
    </p>

    <p style="color:#999; font-size:13px; margin-bottom:20px;">
      If you did not request this verification, you can safely ignore this email.
    </p>

    <hr style="border:none;border-top:1px solid #eee;margin:25px 0;">

    <p style="font-size:13px;color:#666; margin:0;">
      © 2024 Eknal Technologies. All rights reserved.
    </p>
  </div>
</body>
</html>
"""
        
        msg.add_alternative(html_content, subtype="html")
        
        # Use SMTP with proper error handling
        with smtplib.SMTP("smtp.zoho.in", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
            
        logger.info(f"OTP email sent successfully to {to}")
        
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed - check email credentials")
        raise Exception("Email authentication failed")
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {str(e)}")
        raise Exception("Failed to send email")
    except (ConnectionError, TimeoutError, OSError) as e:
        logger.error(f"Network/system error sending email: {str(e)}")
        raise Exception("Email service temporarily unavailable")

def generate_otp():
    """Generate a secure 6-digit OTP"""
    return str(random.randint(100000, 999999))

def save_otp(email, otp):
    """Save OTP to Redis with error handling"""
    if not redis_client:
        raise Exception("OTP storage service unavailable")
    
    try:
        # Store OTP with 5-minute expiration
        redis_client.setex(f"otp:{email}", 300, otp)
        logger.info(f"OTP saved for email: {email}")
    except redis.RedisError as e:
        logger.error(f"Redis error saving OTP: {str(e)}")
        raise Exception("Failed to save verification code")

def get_otp(email):
    """Retrieve OTP from Redis with error handling"""
    if not redis_client:
        return None
    
    try:
        return redis_client.get(f"otp:{email}")
    except redis.RedisError as e:
        logger.error(f"Redis error retrieving OTP: {str(e)}")
        return None

def delete_otp(email):
    """Delete OTP from Redis with error handling"""
    if not redis_client:
        return
    
    try:
        redis_client.delete(f"otp:{email}")
        logger.info(f"OTP deleted for email: {email}")
    except redis.RedisError as e:
        logger.error(f"Redis error deleting OTP: {str(e)}")

def process_otp_request(email):
    """Process OTP request for email verification"""
    try:
        # Generate and send OTP
        otp = generate_otp()
        save_otp(email, otp)
        send_email(email, otp)
        
        logger.info(f"OTP requested for email: {email}")
        return True
    except (smtplib.SMTPException, ConnectionError, OSError) as e:
        logger.error(f"Error in OTP request process: {str(e)}")
        return False

@app.route("/request-edit", methods=["GET", "POST"])
def request_edit():
    """Request OTP for profile editing with improved validation and rate limiting"""
    if request.method == "POST":
        email = sanitize_input(request.form.get("email", ""), 120)
        
        # Basic validation
        if not email:
            flash("Please enter your email address.", "danger")
            return render_template(TEMPLATE_REQUEST_EDIT)
            
        if not validate_email(email):
            flash("Please enter a valid email address.", "danger")
            return render_template(TEMPLATE_REQUEST_EDIT)
        
        # Rate limiting - check if OTP was recently requested
        recent_request = session.get(f"otp_requested_{email}")
        if recent_request:
            flash("Please wait before requesting another verification code.", "danger")
            return render_template(TEMPLATE_REQUEST_EDIT)
        
        # Check if collaborator exists
        collaborator = Collaborator.query.filter_by(email=email).first()
        if not collaborator:
            flash("Email address not found in our records.", "danger")
            return render_template(TEMPLATE_REQUEST_EDIT)

        # Process OTP request
        if process_otp_request(email):
            # Set rate limiting flag (expires in 60 seconds)
            session[f"otp_requested_{email}"] = True
            session["otp_email"] = email
            
            flash("Verification code sent to your email. Please check your inbox.", "success")
            return redirect(url_for("verify_otp"))
        else:
            flash("Unable to send verification code. Please try again later.", "danger")

    return render_template(TEMPLATE_REQUEST_EDIT)
@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    """Verify OTP with improved security and user experience"""
    if request.method == "POST":
        user_otp = sanitize_input(request.form.get("otp", ""), 10)
        email = session.get("otp_email")
        
        if not email:
            flash("Session expired. Please request a new verification code.", "danger")
            return redirect(url_for("request_edit"))
            
        if not user_otp or len(user_otp) != 6 or not user_otp.isdigit():
            flash("Please enter a valid 6-digit verification code.", "danger")
            return render_template("verify_otp.html")
        
        # Check for too many failed attempts
        failed_attempts = session.get(f"otp_attempts_{email}", 0)
        if failed_attempts >= 3:
            session.pop("otp_email", None)
            session.pop(f"otp_attempts_{email}", None)
            flash("Too many failed attempts. Please request a new verification code.", "danger")
            return redirect(url_for("request_edit"))
        
        try:
            saved_otp = get_otp(email)
            
            if saved_otp is None:
                flash("Verification code has expired. Please request a new one.", "danger")
                return redirect(url_for("request_edit"))

            if user_otp == saved_otp:
                # Success - clean up and proceed
                delete_otp(email)
                session["verified_email"] = email
                session.pop("otp_email", None)
                session.pop(f"otp_attempts_{email}", None)
                session.pop(f"otp_requested_{email}", None)
                
                flash("Email verified successfully! You can now update your profile.", "success")
                logger.info(f"OTP verified successfully for email: {email}")
                return redirect(url_for("self_edit_collaborator"))
            else:
                # Increment failed attempts
                session[f"otp_attempts_{email}"] = failed_attempts + 1
                remaining_attempts = 3 - (failed_attempts + 1)
                if remaining_attempts > 0:
                    flash(f"Incorrect verification code. {remaining_attempts} attempts remaining.", "danger")
                else:
                    flash("Incorrect verification code. Please request a new one.", "danger")
                    
        except (redis.RedisError, ConnectionError) as e:
            logger.error(f"Error verifying OTP: {str(e)}")
            flash("Error verifying code. Please try again.", "danger")

    return render_template("verify_otp.html")
def validate_self_edit_input(name, resume_url, contribution):
    """Validate self-edit input data"""
    errors = []
    validated_resume_url = resume_url
    
    if not name:
        errors.append("Please provide your name.")
        
    if not resume_url:
        errors.append("Please provide your resume URL.")
    else:
        # Add http:// if no scheme is provided
        if not resume_url.startswith(VALID_SCHEMES):
            validated_resume_url = HTTPS_SCHEME + resume_url
            
        if not validate_url(validated_resume_url):
            errors.append("Please provide a valid resume URL format.")
            
    if not contribution:
        errors.append("Please provide your contribution description.")
    
    return errors, validated_resume_url

# ---------------- SELF-EDIT FUNCTIONALITY ----------------
@app.route("/self-edit", methods=["GET", "POST"])
def self_edit_collaborator():
    """Allow collaborators to edit their own profiles after OTP verification"""
    email = session.get("verified_email")

    if not email:
        flash("Unauthorized access. Please verify your email first.", "danger")
        return redirect(url_for("request_edit"))

    collaborator = Collaborator.query.filter_by(email=email).first_or_404()

    if request.method == "POST":
        name = sanitize_input(request.form.get("name", ""), 120)
        resume_url = sanitize_input(request.form.get("resume", ""), 500)
        contribution = sanitize_input(request.form.get("contribution", ""), 1000)
        
        # Validate inputs
        validation_errors, validated_resume_url = validate_self_edit_input(name, resume_url, contribution)
        
        if validation_errors:
            for error in validation_errors:
                flash(error, "danger")
            return render_template(TEMPLATE_SELF_EDIT, collaborator=collaborator)

        try:
            # Update collaborator information
            collaborator.name = name
            collaborator.resume_url = validated_resume_url
            collaborator.contribution = contribution
            db.session.commit()

            # Clean up session
            session.pop("verified_email", None)
            session.pop("otp_email", None)

            flash("Your profile has been updated successfully!", "success")
            logger.info(f"Collaborator self-updated profile: {name} ({email})")
            return redirect(url_for("collaborators"))
            
        except (SQLAlchemyError, IntegrityError) as e:
            db.session.rollback()
            flash("Error updating profile. Please try again.", "danger")
            logger.error(f"Error in self-edit: {str(e)}")

    return render_template(TEMPLATE_SELF_EDIT, collaborator=collaborator)

# ---------------- ERROR HANDLERS ----------------
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors gracefully"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors gracefully"""
    db.session.rollback()
    logger.error(f"Internal server error: {str(error)}")
    return render_template('500.html'), 500

@app.errorhandler(413)
def too_large(error):
    """Handle file too large errors"""
    flash("File too large. Please upload a smaller file.", "danger")
    return redirect(url_for("add_file"))

# ---------------- APPLICATION STARTUP ----------------
def create_tables():
    """Create database tables if they don't exist"""
    try:
        with app.app_context():
            db.create_all()
            logger.info("Database tables created successfully")
    except (SQLAlchemyError, OSError) as e:
        logger.error(f"Error creating database tables: {str(e)}")

if __name__ == "__main__":
    create_tables()
    
    # Use environment variable for debug mode
    debug_mode = os.getenv("FLASK_ENV") == "development"
    
    if debug_mode:
        logger.warning("Running in DEBUG mode - do not use in production!")
    
    app.run(
        debug=debug_mode,
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", 5000))
    )
