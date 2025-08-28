# Deployment Guide

This guide covers deploying the Hot Durham Environmental Monitoring System to production environments.

## 🚀 Deployment Overview

### Deployment Options

1. **Traditional Server Deployment** - Direct installation on Linux servers
2. **Docker Containerization** - Containerized deployment with Docker
3. **Cloud Platform Deployment** - AWS, Google Cloud, or Azure
4. **Kubernetes Orchestration** - Scalable container orchestration

## 🔧 Pre-Deployment Checklist

### System Requirements
* [ ] **Operating System**: Ubuntu 20.04+ or CentOS 8+
* [ ] **Python**: Version 3.11 or higher
* [ ] **Memory**: 8GB RAM minimum (16GB recommended)
* [ ] **Storage**: 50GB free space minimum
* [ ] **Network**: Stable internet connection
* [ ] **Ports**: 80, 443, 5000 (configurable)

### Security Requirements
* [ ] SSL/TLS certificates configured
* [ ] Firewall rules implemented
* [ ] API keys secured
* [ ] Database credentials encrypted
* [ ] Backup strategy in place

### Dependencies
* [ ] System packages updated
* [ ] Python virtual environment ready
* [ ] Database server configured
* [ ] Web server (nginx/apache) installed
* [ ] Process supervisor (systemd/supervisor) available

## 🖥️ Traditional Server Deployment

### Step 1: Server Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip \
    nginx postgresql postgresql-contrib redis-server \
    supervisor git curl wget

# Create application user
sudo useradd -m -s /bin/bash hotdurham
sudo usermod -aG sudo hotdurham
```

### Step 2: Application Setup

```bash
# Switch to application user
sudo su - hotdurham

# Clone repository
git clone https://github.com/your-org/hot-durham.git
cd hot-durham

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies (uv preferred)
curl -LsSf https://astral.sh/uv/install.sh | sh || true
uv venv || true
source .venv/bin/activate || true
uv pip sync requirements.txt || true
uv pip sync requirements-dev.txt || true

# Fallback (pip)
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt || true

# Install production dependencies
pip install gunicorn uvicorn[standard]
```

### Step 3: Configuration

```bash
# Create production configuration
cp config/environments/development.py config/environments/production.py

# Edit production settings
nano config/environments/production.py
```

Production configuration template:

```python
# config/environments/production.py
import os

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/hotdurham')

# API Configuration
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
TSI_API_ENDPOINT = os.getenv('TSI_API_ENDPOINT')

# Security
SECRET_KEY = os.getenv('SECRET_KEY')
ALLOWED_HOSTS = ['your-domain.com', 'api.your-domain.com']

# Logging
LOG_LEVEL = 'INFO'
LOG_FILE = '/var/log/hotdurham/app.log'

# Performance
DEBUG = False
CACHE_ENABLED = True
CACHE_TTL = 300

# Monitoring
ENABLE_METRICS = True
METRICS_PORT = 8080
```

### Step 4: Database Setup

```bash
# Create database
sudo -u postgres createdb hotdurham
sudo -u postgres createuser --interactive hotdurham

# Initialize database schema
python src/database/init_db.py --env production

# Run migrations
python scripts/migrate_database.py
```

### Step 5: Environment Variables

```bash
# Create environment file
cat > .env << EOF
ENVIRONMENT=production
DATABASE_URL=postgresql://hotdurham:password@localhost/hotdurham
WEATHER_API_KEY=your_weather_api_key
TSI_API_ENDPOINT=https://your-tsi-endpoint.com
SECRET_KEY=your_secret_key_here
REDIS_URL=redis://localhost:6379/0
EOF

# Secure environment file
chmod 600 .env
```

### Step 6: Web Server Configuration

Create nginx configuration:

```nginx
# /etc/nginx/sites-available/hotdurham
server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL Configuration
    ssl_certificate /etc/ssl/certs/your-domain.crt;
    ssl_certificate_key /etc/ssl/private/your-domain.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    
    # Static files
    location /static/ {
        alias /home/hotdurham/hot-durham/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # API endpoints
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Dashboard
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/hotdurham /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 7: Process Management

Create systemd service:

```ini
# /etc/systemd/system/hotdurham.service
[Unit]
Description=Hot Durham Environmental Monitoring System
After=network.target

[Service]
Type=exec
User=hotdurham
Group=hotdurham
WorkingDirectory=/home/hotdurham/hot-durham
Environment=PATH=/home/hotdurham/hot-durham/venv/bin
ExecStart=/home/hotdurham/hot-durham/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 --timeout 120 src.monitoring.dashboard:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Create background worker service:

```ini
# /etc/systemd/system/hotdurham-worker.service
[Unit]
Description=Hot Durham Background Worker
After=network.target

[Service]
Type=exec
User=hotdurham
Group=hotdurham
WorkingDirectory=/home/hotdurham/hot-durham
Environment=PATH=/home/hotdurham/hot-durham/venv/bin
ExecStart=/home/hotdurham/hot-durham/venv/bin/python scripts/production_manager.py --worker
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable hotdurham hotdurham-worker
sudo systemctl start hotdurham hotdurham-worker
```

## 🐳 Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements*.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements_python311.txt

# Copy application code
COPY . .

# Create non-root user
RUN groupadd -r hotdurham && useradd -r -g hotdurham hotdurham
RUN chown -R hotdurham:hotdurham /app
USER hotdurham

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "src.monitoring.dashboard:app"]
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://hotdurham:password@db:5432/hotdurham
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    restart: unless-stopped

  worker:
    build: .
    command: python scripts/production_manager.py --worker
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://hotdurham:password@db:5432/hotdurham
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    restart: unless-stopped

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=hotdurham
      - POSTGRES_USER=hotdurham
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:6-alpine
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
```

Deploy with Docker Compose:

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Scale workers
docker-compose up -d --scale worker=3
```

## ☁️ Cloud Platform Deployment

### AWS Deployment

**Using AWS ECS:**

```bash
# Install AWS CLI
pip install awscli

# Configure AWS credentials
aws configure

# Create ECS cluster
aws ecs create-cluster --cluster-name hotdurham-cluster

# Build and push Docker image
docker build -t hotdurham .
docker tag hotdurham:latest your-account.dkr.ecr.region.amazonaws.com/hotdurham:latest
docker push your-account.dkr.ecr.region.amazonaws.com/hotdurham:latest
```

**Using AWS Elastic Beanstalk:**

```bash
# Install EB CLI
pip install awsebcli

# Initialize Elastic Beanstalk application
eb init

# Deploy application
eb create production
eb deploy
```

### Google Cloud Platform

```bash
# Install gcloud CLI
curl https://sdk.cloud.google.com | bash

# Initialize gcloud
gcloud init

# Deploy to Google Cloud Run
gcloud run deploy hotdurham \
  --image gcr.io/your-project/hotdurham \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

## 🔍 Monitoring and Maintenance

### Health Checks

```python
# health_check.py
import requests
import sys

def check_health():
    try:
        response = requests.get('http://localhost:5000/health', timeout=10)
        if response.status_code == 200:
            print("✓ Application is healthy")
            return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

if __name__ == "__main__":
    sys.exit(0 if check_health() else 1)
```

### Automated Backups

```bash
#!/bin/bash
# backup.sh

# Database backup
pg_dump hotdurham > /backup/db_$(date +%Y%m%d_%H%M%S).sql

# Application data backup
tar -czf /backup/data_$(date +%Y%m%d_%H%M%S).tar.gz data/ logs/

# Cleanup old backups (keep 30 days)
find /backup -name "*.sql" -mtime +30 -delete
find /backup -name "*.tar.gz" -mtime +30 -delete
```

### Log Rotation

```bash
# /etc/logrotate.d/hotdurham
/home/hotdurham/hot-durham/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
}
```

## 🔒 Security Hardening

### SSL/TLS Configuration

```bash
# Generate SSL certificate (Let's Encrypt)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Firewall Configuration

```bash
# Configure UFW firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 5000/tcp  # Block direct access to app port
sudo ufw enable
```

### Security Headers

Add to nginx configuration:

```nginx
# Security headers
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
add_header Content-Security-Policy "default-src 'self'" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

## 🚨 Troubleshooting Deployment

### Common Issues

1. **Service won't start:**
   ```bash
   sudo systemctl status hotdurham
   sudo journalctl -u hotdurham -f
   ```

2. **Database connection errors:**
   ```bash
   sudo -u postgres psql -c "\l"
   python -c "from src.database.db_manager import DatabaseManager; DatabaseManager().test_connection()"
   ```

3. **Permission issues:**
   ```bash
   sudo chown -R hotdurham:hotdurham /home/hotdurham/hot-durham
   chmod +x scripts/*.py
   ```

### Performance Tuning

```python
# production_tuning.py
import os

# Gunicorn workers calculation
workers = (os.cpu_count() * 2) + 1

# Database connection pool
DB_POOL_SIZE = 20
DB_MAX_OVERFLOW = 30

# Caching configuration
CACHE_CONFIG = {
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': 'redis://localhost:6379/0',
    'CACHE_DEFAULT_TIMEOUT': 300
}
```

## 📋 Post-Deployment Checklist

* [ ] Application starts successfully
* [ ] Database connections working
* [ ] API endpoints responding
* [ ] Dashboard loads correctly
* [ ] SSL certificates valid
* [ ] Monitoring configured
* [ ] Backups automated
* [ ] Log rotation configured
* [ ] Security headers implemented
* [ ] Firewall rules applied
* [ ] Health checks passing
* [ ] Documentation updated

---

*This deployment guide is maintained for the latest version of Hot Durham. For specific deployment questions, consult the [FAQ](FAQ.md) or [Common Issues](Common-Issues.md) guides.*

*Last updated: June 15, 2025*

> NOTE: This deployment guide references a legacy web/dashboard stack. Current repository focus is data ingestion + BigQuery + dbt workflows; adapt or trim components (nginx, gunicorn, Redis) if unused.
