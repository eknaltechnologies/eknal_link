# Eknal Link - Resource & Team Management Platform

A Flask-based web application for managing shared resources, files, and team collaborator information with secure admin authentication and OTP-based self-editing capabilities.

## 🚀 Features

### Core Functionality
- **Resource Management**: Add, edit, and delete useful links and resources
- **File Management**: Upload, preview, download, and manage files securely
- **Team Directory**: Maintain collaborator profiles with contact information and contributions
- **Admin Dashboard**: Full CRUD operations for all resources
- **Self-Service Editing**: Team members can update their profiles using email OTP verification

### Security Features
- Environment-based configuration for sensitive data
- Input validation and sanitization
- File upload security with type and size restrictions
- Rate limiting for OTP requests
- Session management with timeout protection
- Comprehensive error handling and logging

## 📋 Prerequisites

- Python 3.7 or higher
- Redis server (for OTP storage)
- Email account with SMTP access (Zoho Mail recommended)

## 🛠️ Installation & Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd eknal_link
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Copy the example environment file and configure it:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
# Flask Configuration
FLASK_SECRET_KEY=your-super-secret-key-here-change-this-in-production
FLASK_ENV=development
FLASK_HOST=127.0.0.1
FLASK_PORT=5000

# Admin Credentials (Change these!)
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_secure_password

# Email Configuration (Required for OTP)
EMAIL_USER=your_email@zoho.com
EMAIL_PASS=your_app_specific_password
EMAIL_FROM=your_email@zoho.com

# Redis Configuration
REDIS_SERVER_NUMBER=localhost
REDIS_PORT_NUMBER=6379
REDIS_PASSWORD=

# Database & Upload Configuration
DATABASE_URL=sqlite:///data.db
MAX_CONTENT_LENGTH=16777216
UPLOAD_FOLDER=uploads
```

### 5. Setup Redis Server
Install and start Redis server:

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Windows:**
Download and install Redis from the official website or use Docker.

### 6. Initialize Database
```bash
python app.py
```
The database will be created automatically on first run.

## 🚀 Running the Application

### Development Mode
```bash
python app.py
```

### Production Mode
Set environment variables:
```bash
export FLASK_ENV=production
python app.py
```

The application will be available at `http://localhost:5000`

## 📁 Project Structure

```
eknal_link/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env.example          # Environment configuration template
├── .gitignore           # Git ignore rules
├── README.md            # This file
├── static/              # Static assets
│   └── eknal_link.png   # Logo
├── templates/           # HTML templates
│   ├── 404.html         # Error page
│   ├── 500.html         # Error page
│   ├── admin_login.html # Admin login
│   ├── dashboard.html   # Admin dashboard
│   ├── resources.html   # Public resources page
│   ├── collaborators.html # Team directory
│   ├── add_*.html       # Add forms
│   ├── edit_*.html      # Edit forms
│   ├── request_edit.html # OTP request
│   ├── verify_otp.html  # OTP verification
│   └── self_edit.html   # Self-edit form
└── uploads/             # File upload directory (created automatically)
```

## 🔧 Configuration Details

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `FLASK_SECRET_KEY` | Flask session encryption key | Auto-generated | No |
| `FLASK_ENV` | Environment mode | development | No |
| `ADMIN_USERNAME` | Admin login username | admin | No |
| `ADMIN_PASSWORD` | Admin login password | admin123 | No |
| `EMAIL_USER` | SMTP username | - | Yes* |
| `EMAIL_PASS` | SMTP password | - | Yes* |
| `EMAIL_FROM` | From email address | - | Yes* |
| `REDIS_SERVER_NUMBER` | Redis host | localhost | No |
| `REDIS_PORT_NUMBER` | Redis port | 6379 | No |
| `REDIS_PASSWORD` | Redis password | - | No |
| `DATABASE_URL` | Database connection string | sqlite:///data.db | No |
| `MAX_CONTENT_LENGTH` | Max file upload size (bytes) | 16777216 | No |
| `UPLOAD_FOLDER` | File upload directory | uploads | No |

*Required for OTP functionality

### Email Configuration
The application uses SMTP for sending OTP emails. Zoho Mail is recommended:

1. Create a Zoho Mail account
2. Generate an app-specific password
3. Use these settings:
   - SMTP Server: smtp.zoho.in
   - Port: 587
   - Security: STARTTLS

## 🔐 Security Considerations

### Issues Identified & Fixed

1. **✅ Hardcoded Credentials**: Moved to environment variables
2. **✅ Weak Secret Key**: Now uses secure random generation
3. **✅ Input Validation**: Added comprehensive validation for all inputs
4. **✅ File Upload Security**: Enhanced with proper validation and size limits
5. **✅ Error Handling**: Comprehensive error handling and logging
6. **✅ Rate Limiting**: Basic rate limiting for OTP requests
7. **✅ Session Security**: Improved session management

### Remaining Considerations
- Consider implementing CSRF protection for production
- Add HTTPS in production environment
- Implement proper user authentication system for larger teams
- Consider database migrations for schema changes
- Add comprehensive unit tests

## 🎨 UI/UX Improvements

### Current Features
- Responsive design with Tailwind CSS
- Clean, modern interface
- Toast notifications for user feedback
- Gradient backgrounds and smooth animations
- Mobile-friendly layout

### Suggested Enhancements
- Add dark mode toggle
- Implement drag-and-drop file uploads
- Add file preview thumbnails
- Include search and filtering capabilities
- Add bulk operations for admin
- Implement real-time notifications

## 🐛 Known Issues & Limitations

1. **Single Admin User**: Currently supports only one admin account
2. **Basic Authentication**: No role-based access control
3. **File Storage**: Files stored locally (consider cloud storage for production)
4. **Email Dependency**: OTP functionality requires email configuration
5. **Redis Dependency**: OTP storage requires Redis server

## 🚀 Future Enhancements

### Short Term
- [ ] Add CSRF protection
- [ ] Implement file type validation by content
- [ ] Add bulk file operations
- [ ] Create API endpoints for mobile app
- [ ] Add export functionality for collaborator data

### Long Term
- [ ] Multi-tenant support
- [ ] Advanced user roles and permissions
- [ ] Integration with cloud storage (AWS S3, Google Drive)
- [ ] Real-time collaboration features
- [ ] Analytics and reporting dashboard
- [ ] Mobile application

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Team

**Developed by:** [Shalem Raj](https://www.linkedin.com/in/shalem-raj-putta-054388295/) (Python Intern)  
**Company:** [Eknal Technologies](https://eknaltechnologies.in)

## 📞 Support

For support and questions:
- Create an issue in the repository
- Contact: [Eknal Technologies](https://eknaltechnologies.in)

---

**Note**: This application is designed for small to medium teams. For enterprise use, consider additional security measures and scalability improvements.