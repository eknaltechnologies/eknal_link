# Deployment Guide for Eknal Link

This guide covers different deployment options for the Eknal Link application.

## 🐳 Docker Deployment (Recommended)

### Prerequisites
- Docker and Docker Compose installed
- `.env` file configured (copy from `.env.example`)

### Quick Start
```bash
# Clone the repository
git clone <repository-url>
cd eknal_link

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start the application
docker-compose up -d

# View logs
docker-compose logs -f web
```

The application will be available at `http://localhost:5000`

### Stopping the Application
```bash
docker-compose down
```

## 🖥️ Traditional Server Deployment

### Prerequisites
- Python 3.7+
- Redis server
- Nginx (recommended for production)

### Setup Steps

1. **Prepare the server:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv redis-server nginx
```

2. **Clone and setup application:**
```bash
git clone <repository-url>
cd eknal_link
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with production settings
```

4. **Setup systemd service:**
Create `/etc/systemd/system/eknal-link.service`:
```ini
[Unit]
Description=Eknal Link Web Application
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/eknal_link
Environment=PATH=/path/to/eknal_link/venv/bin
ExecStart=/path/to/eknal_link/venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

5. **Start services:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable eknal-link
sudo systemctl start eknal-link
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

6. **Configure Nginx:**
Create `/etc/nginx/sites-available/eknal-link`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/eknal_link/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    client_max_body_size 20M;
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/eknal-link /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## ☁️ Cloud Deployment

### Heroku Deployment

1. **Install Heroku CLI and login:**
```bash
heroku login
```

2. **Create Heroku app:**
```bash
heroku create your-app-name
```

3. **Add Redis addon:**
```bash
heroku addons:create heroku-redis:mini
```

4. **Set environment variables:**
```bash
heroku config:set FLASK_ENV=production
heroku config:set ADMIN_USERNAME=your_admin
heroku config:set ADMIN_PASSWORD=your_password
heroku config:set EMAIL_USER=your_email@domain.com
heroku config:set EMAIL_PASS=your_password
heroku config:set EMAIL_FROM=your_email@domain.com
```

5. **Create Procfile:**
```bash
echo "web: gunicorn run:app" > Procfile
```

6. **Deploy:**
```bash
git add .
git commit -m "Deploy to Heroku"
git push heroku main
```

### AWS EC2 Deployment

1. **Launch EC2 instance** (Ubuntu 20.04 LTS recommended)
2. **Install dependencies** (follow traditional server setup)
3. **Configure security groups** to allow HTTP/HTTPS traffic
4. **Setup SSL certificate** using Let's Encrypt:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 🔧 Production Configuration

### Environment Variables for Production
```env
FLASK_ENV=production
FLASK_SECRET_KEY=your-super-secret-key-minimum-32-characters
ADMIN_USERNAME=your_secure_admin_username
ADMIN_PASSWORD=your_very_secure_password

# Email configuration
EMAIL_USER=your_email@domain.com
EMAIL_PASS=your_app_specific_password
EMAIL_FROM=your_email@domain.com

# Redis configuration
REDIS_SERVER_NUMBER=localhost
REDIS_PORT_NUMBER=6379
REDIS_PASSWORD=your_redis_password

# Database (for PostgreSQL in production)
DATABASE_URL=postgresql://user:password@localhost/eknal_link

# File upload limits
MAX_CONTENT_LENGTH=52428800  # 50MB
UPLOAD_FOLDER=/var/uploads/eknal_link
```

### Security Checklist
- [ ] Change default admin credentials
- [ ] Use strong, unique secret key
- [ ] Enable HTTPS in production
- [ ] Configure firewall rules
- [ ] Set up regular backups
- [ ] Monitor application logs
- [ ] Keep dependencies updated
- [ ] Use environment variables for all secrets
- [ ] Configure Redis password
- [ ] Set up log rotation

### Performance Optimization
- Use a production WSGI server (Gunicorn)
- Configure Nginx for static file serving
- Enable gzip compression
- Set up Redis persistence
- Use PostgreSQL for production database
- Implement CDN for static assets
- Set up monitoring and alerting

## 📊 Monitoring

### Log Files
- Application logs: `app.log`
- Nginx logs: `/var/log/nginx/`
- System logs: `journalctl -u eknal-link`

### Health Checks
The application includes a basic health check endpoint at `/` that returns the resources page.

### Backup Strategy
1. **Database backup:**
```bash
# SQLite
cp instance/data.db backups/data_$(date +%Y%m%d_%H%M%S).db

# PostgreSQL
pg_dump eknal_link > backups/eknal_link_$(date +%Y%m%d_%H%M%S).sql
```

2. **File uploads backup:**
```bash
tar -czf backups/uploads_$(date +%Y%m%d_%H%M%S).tar.gz uploads/
```

## 🚨 Troubleshooting

### Common Issues

1. **Redis connection failed:**
   - Check if Redis server is running
   - Verify Redis configuration in `.env`
   - Check firewall rules

2. **Email not sending:**
   - Verify SMTP credentials
   - Check email provider settings
   - Ensure app-specific password is used

3. **File upload errors:**
   - Check upload directory permissions
   - Verify `MAX_CONTENT_LENGTH` setting
   - Ensure sufficient disk space

4. **Database errors:**
   - Check database file permissions
   - Verify database URL format
   - Run database migrations if needed

### Getting Help
- Check application logs: `tail -f app.log`
- View system logs: `journalctl -u eknal-link -f`
- Check service status: `systemctl status eknal-link`

---

For additional support, please refer to the main README.md or create an issue in the repository.