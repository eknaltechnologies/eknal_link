import os
import re
import json
from flask import Flask, render_template, redirect, url_for, request, flash, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from functools import wraps
from dotenv import load_dotenv
load_dotenv()
import redis
import smtplib
from email.message import EmailMessage
from email.mime.text import MIMEText
from flask_migrate import Migrate
from sqlalchemy import MetaData
import random
import string
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM")
REDIS_SERVER_NUMBER = os.getenv("REDIS_SERVER_NUMBER")
REDIS_PORT_NUMBER = int(os.getenv("REDIS_PORT_NUMBER"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
redis_client = redis.Redis(
    host=REDIS_SERVER_NUMBER,
    port=REDIS_PORT_NUMBER,
    password=REDIS_PASSWORD,
    decode_responses=True
)
# ---------------- APP ----------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", os.urandom(24).hex())
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "instance", "data.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
instance_folder = os.path.join(basedir, "instance")
os.makedirs(instance_folder, exist_ok=True)
UPLOAD_FOLDER = os.path.join("static", "uploads")
DOC_ALLOWED_EXTENSIONS = {"txt", "pdf"}
IMAGE_ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
ALLOWED_EXTENSIONS = DOC_ALLOWED_EXTENSIONS
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["DOC_ALLOWED_EXTENSIONS"] = DOC_ALLOWED_EXTENSIONS
app.config["IMAGE_ALLOWED_EXTENSIONS"] = IMAGE_ALLOWED_EXTENSIONS
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
naming_convention = {"fk": "fk_%(table_name)s_%(referred_table_name)s"}
metadata = MetaData(naming_convention=naming_convention)
db = SQLAlchemy(app, metadata=metadata)
migrate = Migrate(app, db)
# ---------------- ADMIN CREDENTIALS ----------------
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
# ---------------- MODELS ----------------
class Link(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    url = db.Column(db.String(300), nullable=False)
class FileUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    filename = db.Column(db.String(300), nullable=False)
class ContributionType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
class Collaborator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    resume_url = db.Column(db.String(300), nullable=False)
    contribution_type_id = db.Column(db.Integer, db.ForeignKey('contribution_type.id'))
    contribution_type = db.relationship('ContributionType')
    contribution = db.Column(db.String(300), nullable=True)
    linkedin = db.Column(db.String(300), nullable=True)
    github = db.Column(db.String(300), nullable=True)
    source = db.Column(db.String(120), nullable=True)
    photo = db.Column(db.String(300), nullable=True)
class User(db.Model):
    email = db.Column(db.String(120), nullable=False, unique=True)
    name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(120), primary_key=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    Metadata = db.Column(db.String(300), nullable=True)
class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.String(300), nullable=False)
    updated_at = db.Column(db.String(300), nullable=False)
    Metadata = db.Column(db.String(300), nullable=True)
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.String(300), nullable=False)
class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(300), nullable=True)
    date = db.Column(db.String(100), nullable=False)
# ---------------- HELPERS ----------------
log_out="Logged out"
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Admin access only", "danger")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated
def require_password_change(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        username = session.get("user")
        if username and redis_client.exists(f"first_login:{username}"):
            flash("Please change your temporary password before continuing.", "warning")
            return redirect(url_for("change_password"))
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
    return redirect(url_for("admin_login"))
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if session.get("is_admin"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        if (request.form["username"] == ADMIN_USERNAME and
                request.form["password"] == ADMIN_PASSWORD):
            session["is_admin"] = True
            flash("Login successful", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid credentials", "danger")
    return render_template("admin_login.html")
@app.route("/admin-logout")
def admin_logout():
    session.pop("is_admin", None)
    flash(log_out, "info")
    return redirect(url_for("resources"))
# ---------------- PUBLIC RESOURCES ----------------
@app.route("/resources")
@require_password_change
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
@app.route("/add-link", methods=["GET", "POST"])
@admin_required
def add_link():
    if request.method == "POST":
        db.session.add(Link(title=request.form["title"], url=request.form["url"]))
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
        link.url = request.form["url"]
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
# ---------------- FILES ----------------
@app.route("/add-file", methods=["GET", "POST"])
@admin_required
def add_file():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == '' or not allowed_file(file.filename):
            flash("No file selected or invalid file type", "danger")
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
    f = FileUpload.query.get_or_404(id)
    path = os.path.join(UPLOAD_FOLDER, f.filename)
    db.session.delete(f)
    db.session.commit()
    if os.path.exists(path):
        os.remove(path)
    flash("File deleted", "success")
    return redirect(url_for("dashboard"))
# ---------------- CONTRIBUTION TYPES ----------------
@app.route("/contribution-types")
@admin_required
def contribution_types():
    types = ContributionType.query.all()
    return render_template("contribution_types.html", types=types)
@app.route("/add-contribution-type", methods=["GET", "POST"])
@admin_required
def add_contribution_type():
    if request.method == "POST":
        db.session.add(ContributionType(name=request.form["name"]))
        db.session.commit()
        flash("Contribution type added", "success")
        return redirect(url_for("contribution_types"))
    return render_template("add_contribution_type.html")
@app.route("/edit-contribution-type/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_contribution_type(id):
    ctype = ContributionType.query.get_or_404(id)
    if request.method == "POST":
        ctype.name = request.form["name"]
        db.session.commit()
        flash("Contribution type updated", "success")
        return redirect(url_for("contribution_types"))
    return render_template("edit_contribution_type.html", ctype=ctype)
@app.route("/delete-contribution-type/<int:id>", methods=["POST"])
@admin_required
def delete_contribution_type(id):
    ctype = ContributionType.query.get_or_404(id)
    collaborator = Collaborator.query.filter_by(contribution_type_id=id).first()
    if collaborator:
        flash("cannot delete. This contribution type is used by collaborators", "danger")
        return redirect(url_for("contribution_types"))
    db.session.delete(ctype)
    db.session.commit()
    flash("Contribution type deleted", "success")
    return redirect(url_for("contribution_types"))
# ---------------- COLLABORATORS ----------------
@app.route("/collaborators")
def collaborators():
    people = Collaborator.query.all()
    return render_template("collaborators.html", people=people)
@app.route("/add-collaborator", methods=["GET", "POST"])
@admin_required
def add_collaborator():
    types = ContributionType.query.all()
    if request.method == "POST":
        email = request.form["email"].strip()
        if Collaborator.query.filter_by(email=email).first():
            flash("A collaborator with this email already exists", "danger")
            return render_template("add_collaborator.html", types=types)
        collaborator = Collaborator(
            name=request.form["name"],
            email=request.form["email"],
            resume_url=request.form["resume"],
            contribution=request.form["contribution"],
            contribution_type_id=int(request.form["contribution_type"]),
            linkedin=request.form["linkedin"],
            github=request.form["github"],
            source=request.form["source"]
        )
        db.session.add(collaborator)
        db.session.commit()
        try:
            send_collaborator_added_email(collaborator.email, collaborator.name)
        except Exception:
            app.logger.exception("Failed to send collaborator-added email")
            flash("Collaborator added, but email notification failed", "warning")
        flash("Collaborator added", "success")
        return redirect(url_for("collaborators"))
    return render_template("add_collaborator.html", types=types)
@app.route("/edit-collaborator/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_collaborator(id):
    c = Collaborator.query.get_or_404(id)
    types = ContributionType.query.all()
    if request.method == "POST":
        c.name = request.form["name"]
        c.email = request.form["email"]
        c.resume_url = request.form["resume"]
        c.contribution = request.form["contribution"]
        c.contribution_type_id = request.form["contribution_type"]
        c.linkedin = request.form["linkedin"]
        c.github = request.form["github"]
        c.source = request.form["source"]
        db.session.commit()
        flash("Collaborator updated", "success")
        return redirect(url_for("collaborators"))
    return render_template("edit_collaborator.html", collaborator=c, types=types)
@app.route("/delete-collaborator/<int:id>", methods=["POST"])
@admin_required
def delete_collaborator(id):
    c = Collaborator.query.get_or_404(id)
    db.session.delete(c)
    db.session.commit()
    flash("Collaborator deleted", "success")
    return redirect(url_for("collaborators"))
# ---------------- EMAIL HELPERS ----------------
def send_email(to, otp):
    msg = EmailMessage()
    msg["From"] = os.getenv("EMAIL_FROM")
    msg["To"] = to
    msg["Subject"] = "Eknal Technologies – Email Verification Code"
    msg.add_alternative(render_template("otp_email.html", otp=otp), subtype="html")
    server = smtplib.SMTP(os.getenv("EMAIL_HOST"), os.getenv("EMAIL_PORT"))
    server.starttls()
    server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
    server.send_message(msg)
    server.quit()
def send_collaborator_added_email(to, name):
    msg = EmailMessage()
    msg["From"] = os.getenv("EMAIL_FROM")
    msg["To"] = to
    msg["Subject"] = "Welcome to Eknal Link"
    msg.add_alternative(
        render_template("collaborator_email.html", name=name, edit_url=url_for("request_edit", _external=True)),
        subtype="html"
    )
    server = smtplib.SMTP(os.getenv("EMAIL_HOST"), os.getenv("EMAIL_PORT"))
    server.starttls()
    server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
    server.send_message(msg)
    server.quit()
def send_user_credentials_email(to, name, username, password):
    msg = EmailMessage()
    msg["From"] = os.getenv("EMAIL_FROM")
    msg["To"] = to
    msg["Subject"] = "Your Eknal Link account credentials"
    msg.add_alternative(
        f"""<h3>Hello {name},</h3>
        <p>Your account has been created successfully.</p>
        <p><strong>Username:</strong> {username}</p>
        <p><strong>Password:</strong> {password}</p>
        <p>Please log in and change your password after first login.</p>
        <a href="{url_for('login_user', _external=True)}" style="display:inline-block; background-color:#4CAF50; color:white; padding:10px 20px; border-radius:5px; text-decoration:none;">Login</a>""",
        subtype="html"
    )
    server = smtplib.SMTP(os.getenv("EMAIL_HOST"), os.getenv("EMAIL_PORT"))
    server.starttls()
    server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
    server.send_message(msg)
    server.quit()
def generate_temporary_password(length=12):
    alphabet = string.ascii_letters + string.digits
    return ''.join(random.choice(alphabet) for _ in range(length))
def generate_otp():
    return str(random.randint(100000, 999999))
def current_timestamp():
    return datetime.now().isoformat(sep=" ", timespec="seconds")
def save_otp(email, otp):
    redis_client.setex(f"otp:{email}", 300, otp)
def get_otp(email):
    return redis_client.get(f"otp:{email}")
def delete_otp(email):
    redis_client.delete(f"otp:{email}")
# ---------------- COLLABORATOR SELF-EDIT ----------------
@app.route("/request-edit", methods=["GET", "POST"])
def request_edit():
    if request.method == "POST":
        email = request.form["email"].strip()
        if not email:
            flash("Please enter your email address", "danger")
            return redirect(url_for("request_edit"))
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            flash("Invalid email format", "danger")
            return redirect(url_for("request_edit"))
        collaborator = Collaborator.query.filter_by(email=email).first()
        if not collaborator:
            flash("Email not found", "danger")
            return redirect(url_for("request_edit"))
        otp = generate_otp()
        save_otp(email, otp)
        send_email(email, otp)
        session["otp_email"] = email
        flash("Verification code sent to your email.", "success")
        return redirect(url_for("verify_otp"))
    return render_template("request_edit.html")
@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if request.method == "POST":
        user_otp = request.form["otp"]
        email = session.get("otp_email")
        if not email:
            flash("Session expired", "danger")
            return redirect(url_for("request_edit"))
        saved_otp = redis_client.get(f"otp:{email}")
        if saved_otp is None:
            flash("OTP expired", "danger")
            return redirect(url_for("request_edit"))
        if user_otp == saved_otp:
            redis_client.delete(f"otp:{email}")
            session["verified_email"] = email
            flash("OTP verified successfully.", "success")
            return redirect(url_for("self_edit_collaborator"))
        flash("Incorrect OTP. Please try again.", "danger")
    return render_template("verify_otp.html")
@app.route("/self-edit", methods=["GET", "POST"])
def self_edit_collaborator():
    email = session.get("verified_email")
    if not email:
        flash("Unauthorized access", "danger")
        return redirect(url_for("request_edit"))
    collaborator = Collaborator.query.filter_by(email=email).first_or_404()
    if request.method == "POST":
        collaborator.name = request.form["name"]
        collaborator.resume_url = request.form["resume"]
        collaborator.contribution = request.form["contribution"]
        photo = request.files.get("photo")
        if photo and allowed_file(photo.filename):
            if collaborator.photo and collaborator.photo != "default.png":
                old_path = os.path.join(app.config["UPLOAD_FOLDER"], collaborator.photo)
                if os.path.exists(old_path):
                    os.remove(old_path)
            filename = f"{datetime.now().timestamp()}_{secure_filename(photo.filename)}"
            photo.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            collaborator.photo = filename
        db.session.commit()
        session.pop("verified_email")
        session.pop("otp_email", None)
        flash("Your profile has been updated successfully.", "success")
        return redirect(url_for("collaborators"))
    return render_template("self_edit.html", collaborator=collaborator)
# ---------------- ROLES ----------------
@app.route("/create-role", methods=["GET", "POST"])
@admin_required
def create_role():
    if request.method == "POST":
        name = request.form["role_name"]
        description = request.form.get("description", "").strip()
        selected_access = request.form.getlist("access")
        valid_access = {"read", "write", "update", "delete"}
        selected_access = [perm for perm in selected_access if perm in valid_access]
        if not name:
            flash("Role name cannot be empty", "danger")
            return redirect(url_for("create_role"))
        if not selected_access:
            flash("Select at least one access permission", "danger")
            return redirect(url_for("create_role"))
        if not description:
            flash("Description cannot be empty", "danger")
            return redirect(url_for("create_role"))
        now = current_timestamp()
        role_metadata = json.dumps({"description": description, "access": selected_access})
        new_role = Role(name=name, created_at=now, updated_at=now, Metadata=role_metadata)
        db.session.add(new_role)
        db.session.commit()
        flash("Role created successfully", "success")
        return redirect(url_for("dashboard"))
    return render_template("create_role.html")
# ---------------- USERS ----------------
@app.route("/create-users", methods=["GET", "POST"])
@admin_required
def create_user():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        name = request.form["name"]
        role_id = request.form["role_id"]
        if not all([username, email, name, role_id]):
            flash("All fields are required", "danger")
            return redirect(url_for("create_user"))
        if User.query.filter_by(username=username).first():
            flash("Username already exists", "danger")
            return redirect(url_for("create_user"))
        if User.query.filter_by(email=email).first():
            flash("Email already exists", "danger")
            return redirect(url_for("create_user"))
        generated_password = generate_temporary_password()
        redis_client.setex(f"temp_pass:{username}", 86400, generated_password)
        new_user = User(username=username, password="", email=email, name=name, role_id=int(role_id))
        db.session.add(new_user)
        db.session.commit()
        try:
            send_user_credentials_email(to=email, name=name, username=username, password=generated_password)
            flash("User created and credentials sent by email", "success")
        except Exception:
            app.logger.exception("Failed to send user credentials email")
            flash("User created, but failed to send credentials email", "warning")
        return redirect(url_for("resources"))
    roles = Role.query.all()
    return render_template("create_user.html", roles=roles)
# ---------------- USER LOGIN ----------------
@app.route("/user-login", methods=["GET", "POST"])
def login_user():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            flash("Please enter both username and password", "danger")
            return render_template("user_login.html")
        current_user = User.query.filter_by(username=username).first()
        if current_user:
            if current_user.password and check_password_hash(current_user.password, password):
                session["user"] = current_user.username
                flash("Login successful", "success")
                return redirect(url_for("user_dashboard"))
            temp_pass = redis_client.get(f"temp_pass:{username}")
            if password == temp_pass:
                session["user"] = current_user.username
                redis_client.setex(f"first_login:{username}", 900, "true")
                session["verified_email"] = current_user.email
                flash("Please change your temporary password before continuing.", "warning")
                return redirect(url_for("change_password"))
        flash("Invalid username or password", "danger")
    return render_template("user_login.html")
# ---------------- FORGOT PASSWORD ----------------
@app.route("/user/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"].strip()
        user = User.query.filter_by(email=email).first()
        if user:
            otp = generate_otp()
            save_otp(email, otp)
            send_email(email, otp)
            session["otp_email"] = email
            flash("OTP sent to your email", "success")
            return redirect(url_for("verify_otpuser"))
        flash("Email not found", "danger")
    return render_template("forget_password.html")
@app.route("/verify-otpUser", methods=["GET", "POST"])
def verify_otpuser():
    if request.method == "POST":
        user_otp = request.form.get("otp")
        email = session.get("otp_email")
        if not email:
            flash("Session expired", "danger")
            return redirect(url_for("forgot_password"))
        saved_otp = redis_client.get(f"otp:{email}")
        if saved_otp is None:
            flash("OTP expired", "danger")
            return redirect(url_for("forgot_password"))
        if user_otp == saved_otp:
            redis_client.delete(f"otp:{email}")
            session["verified_email"] = email
            flash("OTP verified successfully.", "success")
            return redirect(url_for("change_password"))
        flash("Incorrect OTP. Please try again.", "danger")
    return render_template("Verify_otpUser.html")
@app.route("/change-password", methods=["GET", "POST"])
def change_password():
    email = session.get("verified_email")
    if not email:
        flash("Unauthorized access", "danger")
        return redirect(url_for("forgot_password"))
    user = User.query.filter_by(email=email).first_or_404()
    if request.method == "POST":
        new_password = request.form["New_password"]
        confirm_password = request.form["confirm_password"]
        if new_password != confirm_password:
            flash("Passwords do not match", "danger")
            return render_template("Reset_password.html")
        user.password = generate_password_hash(new_password)
        db.session.commit()
        redis_client.delete(f"first_login:{user.username}")
        redis_client.delete(f"temp_pass:{user.username}")
        session.pop("verified_email", None)
        session.pop("otp_email", None)
        flash("Password changed successfully. Please log in.", "success")
        return redirect(url_for("login_user"))
    return render_template("Reset_password.html")
@app.route("/user-logout",methods=["GET"])
def user_logout():
    session.pop("user", None)
    flash(log_out, "info")
    return redirect(url_for("login_user"))
@app.route("/user-dashboard",methods=['GET'])
def user_dashboard():
    if not session.get("user"):
        flash("Please login first", "danger")
        return redirect(url_for("login_user"))
    current_user = User.query.filter_by(username=session.get("user")).first()
    return render_template("user_dashboard.html", current_user=current_user)# ---------------- POSTS ----------------
@app.route("/posts",methods=["GET"])
def post_list():
    posts = Post.query.order_by(Post.id.desc()).all()
    return render_template("posts.html", posts=posts)
@app.route("/create-post", methods=["GET", "POST"])
@admin_required
def create_post():
    if request.method == "POST":
        title = request.form["title"].strip()
        content = request.form["content"].strip()
        if not title or not content:
            flash("Title and content are required", "danger")
            return render_template("create_post.html")
        image_filename = None
        image = request.files.get("image")
        if image and image.filename and allowed_file(image.filename):
            image_filename = f"{datetime.now().timestamp()}_{secure_filename(image.filename)}"
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))
        db.session.add(Post(title=title, content=content, image=image_filename, created_at=current_timestamp()))
        db.session.commit()
        flash("Post created", "success")
        return redirect(url_for("post_list"))
    return render_template("create_post.html")
@app.route("/edit-post/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_post(id):
    post = Post.query.get_or_404(id)
    if request.method == "POST":
        post.title = request.form["title"].strip()
        post.content = request.form["content"].strip()
        image = request.files.get("image")
        if image and image.filename and allowed_file(image.filename):
            if post.image:
                old_path = os.path.join(app.config["UPLOAD_FOLDER"], post.image)
                if os.path.exists(old_path):
                    os.remove(old_path)
            post.image = f"{datetime.now().timestamp()}_{secure_filename(image.filename)}"
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], post.image))
        db.session.commit()
        flash("Post updated", "success")
        return redirect(url_for("post_list"))
    return render_template("edit_post.html", post=post)
@app.route("/delete-post/<int:id>", methods=["POST"])
@admin_required
def delete_post(id):
    post = Post.query.get_or_404(id)
    if post.image:
        path = os.path.join(app.config["UPLOAD_FOLDER"], post.image)
        if os.path.exists(path):
            os.remove(path)
    db.session.delete(post)
    db.session.commit()
    flash("Post deleted", "success")
    return redirect(url_for("post_list"))
# ---------------- ACTIVITIES ----------------
@app.route("/activities",methods=["GET"])
def post_activity():
    activities = Activity.query.order_by(Activity.id.desc()).all()
    return render_template("eknal_activities.html", activities=activities)
@app.route("/add-activity", methods=["GET", "POST"])
@admin_required
def add_activity():
    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        date = request.form["date"].strip()
        if not title or not description or not date:
            flash("All fields are required", "danger")
            return render_template("add_activity.html")
        image_filename = None
        image = request.files.get("image")
        if image and image.filename and allowed_file(image.filename):
            image_filename = f"{datetime.now().timestamp()}_{secure_filename(image.filename)}"
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))
        db.session.add(Activity(title=title, description=description, image=image_filename, date=date))
        db.session.commit()
        flash("Activity added", "success")
        return redirect(url_for("post_activity"))
    return render_template("add_activity.html")
@app.route("/edit-activity/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_activity(id):
    activity = Activity.query.get_or_404(id)
    if request.method == "POST":
        activity.title = request.form["title"].strip()
        activity.description = request.form["description"].strip()
        activity.date = request.form["date"].strip()
        image = request.files.get("image")
        if image and image.filename and allowed_file(image.filename):
            if activity.image:
                old_path = os.path.join(app.config["UPLOAD_FOLDER"], activity.image)
                if os.path.exists(old_path):
                    os.remove(old_path)
            activity.image = f"{datetime.now().timestamp()}_{secure_filename(image.filename)}"
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], activity.image))
        db.session.commit()
        flash("Activity updated", "success")
        return redirect(url_for("post_activity"))
    return render_template("edit_activity.html", activity=activity)
@app.route("/delete-activity/<int:id>", methods=["POST"])
@admin_required
def delete_activity(id):
    activity = Activity.query.get_or_404(id)
    if activity.image:
        path = os.path.join(app.config["UPLOAD_FOLDER"], activity.image)
        if os.path.exists(path):
            os.remove(path)
    db.session.delete(activity)
    db.session.commit()
    flash("Activity deleted", "success")
    return redirect(url_for("post_activity"))
@app.context_processor
def inject_current_user():
    user_email = session.get("user")
    
    if user_email:
        current_user = Collaborator.query.filter_by(
            email=user_email
        ).first()

        return {"cuser":current_user}

    return {"cuser":None}
# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=False, port=9123)
