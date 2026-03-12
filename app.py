import os
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
import random
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
app.config["SECRET_KEY"] = os.getenv"super-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

db = SQLAlchemy(app)

# ---------------- ADMIN CREDENTIALS ----------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# ---------------- MODELS ----------------
class Link(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    url = db.Column(db.String(300), nullable=False)

class FileUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    filename = db.Column(db.String(300), nullable=False)

class Collaborator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    resume_url = db.Column(db.String(300), nullable=False)
    contribution = db.Column(db.String(300), nullable=False)

# ---------------- HELPERS ----------------
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
    if session.get("is_admin"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        if (
            request.form["username"] == ADMIN_USERNAME and
            request.form["password"] == ADMIN_PASSWORD
        ):
            session["is_admin"] = True
            flash("Login successful", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials", "danger")

    return render_template("admin_login.html")

@app.route("/admin-logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("Logged out", "info")
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
    if request.method == "POST":
        db.session.add(Link(
            title=request.form["title"],
            url=request.form["url"]
        ))
        db.session.commit()
        flash("Link added", "success")
        return redirect(url_for("dashboard"))
    return render_template("add_link.html")

@app.route("/edit-link/<int:id>", methods=["GET","POST"])
@admin_required
def edit_link(id):
    link = Link.query.get_or_404(id)

    if request.method == "POST":
        link.title = request.form["title"]
        link.url = request.form["url"]
        db.session.commit()
        flash("Link updated", "success")
        return redirect(url_for("dashboard"))

    return render_template("edit_link.html", link=link)\

@app.route("/delete-link/<int:id>", methods=["POST"])
@admin_required
def delete_link(id):
    link = Link.query.get_or_404(id)
    db.session.delete(link)
    db.session.commit()
    flash("Link deleted", "success")
    return redirect(url_for("dashboard"))

# ---------------- FILES ----------------
@app.route("/add-file", methods=["GET","POST"])
@admin_required
def add_file():
    if request.method == "POST":
        file = request.files["file"]

        if not allowed_file(file.filename):
            flash("Invalid file type", "danger")
            return redirect(url_for("add_file"))

        filename = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

        db.session.add(FileUpload(
            title=request.form["title"],
            filename=filename
        ))
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
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        file.filename,
        as_attachment=False  
    )
@app.route("/delete-file/<int:id>", methods=["POST"])
@admin_required
def delete_file(id):
    f = FileUpload.query.get_or_404(id)

    path = os.path.join(UPLOAD_FOLDER, f.filename)
    if os.path.exists(path):
        os.remove(path)

    db.session.delete(f)
    db.session.commit()
    flash("File deleted", "success")
    return redirect(url_for("dashboard"))

# ---------------- COLLABORATORS ----------------
@app.route("/collaborators")
def collaborators():
    people = Collaborator.query.all()
    return render_template("collaborators.html", people=people)

@app.route("/add-collaborator", methods=["GET","POST"])
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

@app.route("/edit-collaborator/<int:id>", methods=["GET","POST"])
@admin_required
def edit_collaborator(id):
    c = Collaborator.query.get_or_404(id)

    if request.method == "POST":
        c.name = request.form["name"]
        c.email = request.form["email"]
        c.resume_url = request.form["resume"]
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
    return redirect(url_for("collaborators"))

def send_email(to, otp):
    msg = EmailMessage()
    msg["From"] = os.getenv("EMAIL_FROM")
    msg["To"] = to
    msg["Subject"] = "Eknal Technologies – Email Verification Code"
   # msg.set_content(f"Your OTP for editing your profile is: {otp}")
    msg.add_alternative(f"""
<html>
<body style="background-color:#f4f6fb; font-family: Arial, sans-serif; padding:30px;">

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

    <h2 style="color:#4f46e5; margin-bottom:10px;">
      OTP Verification
    </h2>

    <p style="color:#555; font-size:15px;">
      We received a request to update your collaborator profile.
    </p>

    <p style="color:#555; font-size:15px;">
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
    ">
      {otp}
    </div>

    <p style="color:#777; font-size:14px;">
      This code is valid for 5 minutes.
    </p>

    <p style="color:#999; font-size:13px;">
      If you did not request this, you can safely ignore this email.
    </p>

    <hr style="border:none;border-top:1px solid #eee;margin:25px 0;">

    <p style="font-size:13px;color:#666;">
      © Eknal Technologies
    </p>

  </div>

</body>
</html>
""", subtype="html")
    server = smtplib.SMTP("smtp.zoho.in", 587)
    server.starttls()
    server.login(
        os.getenv("EMAIL_USER"),
        os.getenv("EMAIL_PASS")
    )
    server.send_message(msg)
    server.quit()
def generate_otp():
    return str(random.randint(100000, 999999))

def save_otp(email, otp):
    redis_client.setex(f"otp:{email}", 300, otp)

def get_otp(email):
    return redis_client.get(f"otp:{email}")

def delete_otp(email):
    redis_client.delete(f"otp:{email}")

@app.route("/request-edit", methods=["GET", "POST"])
def request_edit():
    if request.method == "POST":
        # from datetime import datetime
        # datetime=datetime.now()
        # print(datetime)
        from time import perf_counter
        start=perf_counter()
        email = request.form["email"].strip()
        

        # 1) Empty check
        if not email:
            flash("Please enter your email address", "danger")
            return redirect(url_for("request_edit"))

    
        # 3) Check in database
        collaborator = Collaborator.query.filter_by(email=email).first()

        if not collaborator:
            flash("Email not found", "danger")
            return redirect(url_for("request_edit"))

        # 4) Generate + Send OTP
        otp = generate_otp()
        duration=perf_counter()-start
        print(f"{duration:.4f} seconds 367")
        start=perf_counter()
        save_otp(email, otp)
        duration=perf_counter()-start
        print(f"{duration:.4f} seconds 371")
        start=perf_counter()
        
        send_email(email, otp)
        duration=perf_counter()-start
        print(f"{duration:.4f} seconds 376")
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
#edit
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

        db.session.commit()

        session.pop("verified_email")
        session.pop("otp_email", None)

        flash("Your profile has been updated successfully.", "success")
        return redirect(url_for("collaborators"))

    return render_template("self_edit.html", collaborator=collaborator)

# ---------------- RUN ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run()
