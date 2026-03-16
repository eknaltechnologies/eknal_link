# Eknal Link Platform – Technical Overhaul

This repository contains the improved and secured version of the Eknal Link platform, completed as part of a technical internship evaluation challenge.

🏆 **Final Submission Status: Passed SonarCloud Quality Gate**
- **0** Security Hotspots
- **0%** Code Duplication 
- **0** New Issues

## 🚀 Key Improvements & Bug Fixes

### 🛡️ Security & Reliability
- **CSRF Protection**: Integrated `Flask-WTF` to secure all POST forms across the application.
- **Rate Limiting**: Implemented `Flask-Limiter` on critical endpoints (`/admin-login`, `/request-edit`, `/resend-otp`) to prevent brute-force and spam attacks.
- **Environment Management**: Moved all sensitive data (Secret Keys, DB URIs, Admin Credentials) to a `.env` structure using `python-dotenv`.
- **Redis Resilience**: Added a robust **In-Memory Fallback Store** for OTPs. If Redis is unavailable, the application automatically switches to local memory storage, ensuring 100% uptime for the verification system.
- **File Security**: Enforced a `10MB` upload limit and strict filename/extension validation.
- **Secret Key Stability**: Fixed a vulnerability where sessions were invalidated on every server restart due to dynamic key rotation.

### 🎨 Frontend & UX Overhaul
- **Modern UI Design**: Rebuilt the interface using **Tailwind CSS**, featuring:
  - Glassmorphism containers and backdrops.
  - Vibrant gradient interaction states.
  - Responsive, mobile-first navigation.
  - Consistent typography using the *Inter* font.
- **Template Inheritance**: Refactored the entire frontend to use **Jinja2 inheritance** (`base.html`), eliminating code duplication and ensuring a unified look and feel.
- **Auto-Fill Security**: Disabled browser credential autocompletion on the admin login page for enhanced security.
- **Dynamic UX**: Added active link highlighting, polished empty-state messages for empty resources, and improved toast notification lifecycle.

### 🛠️ Features & Quality of Life
- **OTP Resend System**: Added the ability for users to safely request a new verification code if their session or code expires.
- **Email Integration**: Fully configured for Zoho SMTP with secure App Password authentication.
- **SEO Ready**: Added unique page titles and meta descriptions for all public routes.
- **Dependency Management**: Added `requirements.txt` for standardized and easy project replication.

## ⚙️ Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/eknaltechnologies/eknal_link.git
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   - Create a `.env` file based on `.env.example`.
   - Add your `SECRET_KEY`, `ADMIN_PASSWORD`, and Zoho SMTP credentials.

4. **Run the Application**:
   ```bash
   python app.py
   ```
