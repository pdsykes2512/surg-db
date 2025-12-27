# Deployment Guide

Complete guide for deploying the Surgical Outcomes Database to production environments.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Server Requirements](#server-requirements)
- [Deployment Options](#deployment-options)
- [Production Setup](#production-setup)
- [Security Hardening](#security-hardening)
- [Backup and Recovery](#backup-and-recovery)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software
- **Operating System**: Ubuntu 22.04 LTS or later (recommended)
- **Python**: 3.10 or higher
- **Node.js**: 18 LTS or higher
- **MongoDB**: 6.0 or higher
- **Nginx**: 1.18 or higher (reverse proxy)
- **SSL/TLS**: Certbot for Let's Encrypt certificates

### Domain Requirements
- Domain name with DNS configured
- SSL/TLS certificate (Let's Encrypt recommended)

## Server Requirements

### Minimum Requirements
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Storage**: 50 GB SSD
- **Network**: 100 Mbps

### Recommended for Production
- **CPU**: 4 cores
- **RAM**: 8 GB
- **Storage**: 200 GB SSD with backup
- **Network**: 1 Gbps
- **Load Balancer**: If high traffic expected

## Deployment Options

### Option 1: Single Server Deployment
Best for small to medium deployments (< 1000 concurrent users)

```
┌─────────────────────────────────────┐
│         Nginx (Port 80/443)         │
│    (Reverse Proxy + SSL/TLS)        │
└───────────┬─────────────────────────┘
            │
    ┌───────┴───────┐
    │               │
┌───▼────┐    ┌────▼─────┐
│Frontend│    │  Backend │
│  :5173 │    │   :8000  │
└────────┘    └──────┬───┘
                     │
              ┌──────▼─────┐
              │  MongoDB   │
              │   :27017   │
              └────────────┘
```

### Option 2: Containerized Deployment (Docker)
Best for portability and scalability

### Option 3: Cloud Deployment
- AWS: EC2 + RDS/DocumentDB
- Google Cloud: Compute Engine + Cloud MongoDB
- Azure: Virtual Machines + Cosmos DB

## Production Setup

### 1. System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.10 python3-pip nodejs npm nginx mongodb-server

# Install process manager
sudo npm install -g pm2

# Install certbot for SSL
sudo apt install -y certbot python3-certbot-nginx
```

### 2. MongoDB Setup

```bash
# Enable MongoDB authentication
sudo systemctl start mongod
mongosh

# In MongoDB shell:
use admin
db.createUser({
  user: "dbAdmin",
  pwd: "STRONG_PASSWORD_HERE",
  roles: [ { role: "userAdminAnyDatabase", db: "admin" } ]
})

use surgical_outcomes
db.createUser({
  user: "surgicalapp",
  pwd: "STRONG_PASSWORD_HERE",
  roles: [ { role: "readWrite", db: "surgical_outcomes" } ]
})
exit

# Edit MongoDB config to enable auth
sudo nano /etc/mongod.conf
```

Add to `/etc/mongod.conf`:
```yaml
security:
  authorization: enabled

net:
  bindIp: 127.0.0.1
  port: 27017
```

```bash
# Restart MongoDB
sudo systemctl restart mongod
sudo systemctl enable mongod
```

### 3. Application Setup

```bash
# Create application user
sudo useradd -m -s /bin/bash surgapp
sudo su - surgapp

# Clone repository
git clone https://github.com/pdsykes2512/surg-db.git
cd surg-db
```

### 4. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn

# Create production .env
cat > .env << EOF
MONGODB_URL=mongodb://surgicalapp:STRONG_PASSWORD_HERE@localhost:27017/surgical_outcomes?authSource=surgical_outcomes
DATABASE_NAME=surgical_outcomes
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
CORS_ORIGINS=https://yourdomain.com
EOF

# Initialize database
python -m app.database

# Create admin user
cd ../execution
python create_admin_user.py
cd ../backend
```

### 5. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Create production .env
cat > .env.production << EOF
VITE_API_URL=https://api.yourdomain.com
EOF

# Build for production
npm run build

# This creates a 'dist' folder with optimized assets
```

### 6. Configure PM2 (Backend Process Manager)

```bash
# Return to app directory
cd ~/surg-db

# Create PM2 ecosystem file
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'surgical-backend',
    script: './backend/venv/bin/gunicorn',
    args: 'app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000',
    cwd: './backend',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production'
    }
  }]
}
EOF

# Start application
pm2 start ecosystem.config.js

# Save PM2 configuration
pm2 save

# Setup PM2 to start on boot
pm2 startup
# Follow the instructions provided by PM2
```

### 7. Configure Nginx

```bash
# Exit surgapp user
exit

# Create Nginx configuration
sudo nano /etc/nginx/sites-available/surgical-outcomes
```

Add the following configuration:
```nginx
# Backend API
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}

# Frontend
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    root /home/surgapp/surg-db/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/surgical-outcomes /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 8. Setup SSL/TLS with Let's Encrypt

```bash
# Obtain certificates
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com -d api.yourdomain.com

# Certbot will automatically configure Nginx for HTTPS

# Test auto-renewal
sudo certbot renew --dry-run
```

### Alternative: Using Caddy as Reverse Proxy

Caddy is a modern, automatic HTTPS web server that's simpler to configure than Nginx. It automatically obtains and renews SSL certificates.

#### 1. Install Caddy

```bash
# Install Caddy (Ubuntu/Debian)
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

#### 2. Configure Caddy

```bash
# Create Caddyfile
sudo nano /etc/caddy/Caddyfile
```

Add the following configuration:

```caddy
# Backend API
api.yourdomain.com {
    reverse_proxy localhost:8000 {
        # Health check
        health_uri /api/health
        health_interval 30s
        health_timeout 5s

        # Headers
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }

    # Enable compression
    encode gzip

    # Security headers
    header {
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
        Permissions-Policy "geolocation=(), microphone=(), camera=()"
    }

    # Logging
    log {
        output file /var/log/caddy/api-access.log
        format json
    }
}

# Frontend
yourdomain.com, www.yourdomain.com {
    root * /home/surgapp/surg-db/frontend/dist

    # Try files first, fallback to index.html for SPA routing
    try_files {path} /index.html
    file_server

    # Cache static assets
    @static {
        path *.js *.css *.png *.jpg *.jpeg *.gif *.ico *.svg *.woff *.woff2 *.ttf *.eot
    }
    header @static Cache-Control "public, max-age=31536000, immutable"

    # Enable compression
    encode gzip

    # Security headers
    header {
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
    }

    # Logging
    log {
        output file /var/log/caddy/frontend-access.log
        format json
    }
}
```

#### 3. Start Caddy

```bash
# Create log directory
sudo mkdir -p /var/log/caddy
sudo chown caddy:caddy /var/log/caddy

# Test configuration
sudo caddy validate --config /etc/caddy/Caddyfile

# Restart Caddy
sudo systemctl restart caddy
sudo systemctl enable caddy

# Check status
sudo systemctl status caddy
```

#### 4. View Caddy Logs

```bash
# Access logs
sudo tail -f /var/log/caddy/frontend-access.log
sudo tail -f /var/log/caddy/api-access.log

# System logs
sudo journalctl -u caddy -f
```

#### Advantages of Caddy

- **Automatic HTTPS**: Obtains and renews certificates automatically
- **Simpler Configuration**: More readable than Nginx
- **HTTP/2 and HTTP/3**: Enabled by default
- **Modern Defaults**: Secure defaults out of the box
- **No External Tools**: No need for certbot

#### Caddy vs Nginx Comparison

| Feature | Caddy | Nginx |
|---------|-------|-------|
| Auto HTTPS | ✅ Automatic | ❌ Requires certbot |
| Configuration | Simple, readable | More verbose |
| HTTP/3 | ✅ Built-in | Requires extra build |
| Community | Growing | Very large |
| Performance | Excellent | Excellent |
| Learning Curve | Easy | Moderate |

## Security Hardening

### 1. Firewall Configuration

```bash
# Enable UFW
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable

# Verify
sudo ufw status
```

### 2. MongoDB Security

```bash
# Edit MongoDB config
sudo nano /etc/mongod.conf
```

Add:
```yaml
security:
  authorization: enabled

net:
  bindIp: 127.0.0.1  # Only local connections

setParameter:
  enableLocalhostAuthBypass: false
```

### 3. Application Security

- Change default admin password immediately
- Rotate JWT SECRET_KEY regularly
- Enable rate limiting (optional: install nginx-extras)
- Set up fail2ban for brute force protection

```bash
# Install fail2ban
sudo apt install fail2ban

# Create custom jail
sudo nano /etc/fail2ban/jail.local
```

Add:
```ini
[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 5
bantime = 600
```

### 4. Regular Updates

```bash
# Create update script
cat > ~/update.sh << 'EOF'
#!/bin/bash
sudo apt update && sudo apt upgrade -y
pm2 update
sudo certbot renew
EOF

chmod +x ~/update.sh

# Add to cron (weekly)
crontab -e
# Add: 0 2 * * 0 /home/surgapp/update.sh
```

## Backup and Recovery

### 1. MongoDB Backup

```bash
# Create backup script
cat > ~/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/mongodb"
mkdir -p $BACKUP_DIR

mongodump --uri="mongodb://surgicalapp:PASSWORD@localhost:27017/surgical_outcomes?authSource=surgical_outcomes" --out=$BACKUP_DIR/$DATE

# Keep only last 7 days
find $BACKUP_DIR -type d -mtime +7 -exec rm -rf {} +
EOF

chmod +x ~/backup.sh

# Daily backup at 2 AM
crontab -e
# Add: 0 2 * * * /home/surgapp/backup.sh
```

### 2. Application Backup

```bash
# Backup application code and configs
tar -czf ~/surg-db-backup-$(date +%Y%m%d).tar.gz ~/surg-db
```

### 3. Recovery

```bash
# Restore MongoDB
mongorestore --uri="mongodb://surgicalapp:PASSWORD@localhost:27017/surgical_outcomes?authSource=surgical_outcomes" /backup/mongodb/TIMESTAMP/surgical_outcomes

# Restore application
tar -xzf ~/surg-db-backup-YYYYMMDD.tar.gz -C ~/
```

## Monitoring

### 1. PM2 Monitoring

```bash
# View logs
pm2 logs surgical-backend

# Monitor resources
pm2 monit

# View status
pm2 status
```

### 2. System Monitoring

```bash
# Install monitoring tools
sudo apt install htop iotop

# Monitor MongoDB
mongosh --eval "db.serverStatus()"
```

### 3. Application Logs

```bash
# Backend logs
tail -f ~/surg-db/backend/logs/app.log

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

## Troubleshooting

### Backend Not Starting

```bash
# Check PM2 status
pm2 status

# View logs
pm2 logs surgical-backend --lines 100

# Check if port 8000 is in use
sudo lsof -i :8000

# Restart backend
pm2 restart surgical-backend
```

### Frontend Not Loading

```bash
# Check Nginx configuration
sudo nginx -t

# Check Nginx status
sudo systemctl status nginx

# View Nginx error log
sudo tail -f /var/log/nginx/error.log

# Restart Nginx
sudo systemctl restart nginx
```

### Database Connection Issues

```bash
# Check MongoDB status
sudo systemctl status mongod

# Check MongoDB logs
sudo tail -f /var/log/mongodb/mongod.log

# Test connection
mongosh --host localhost --port 27017 -u surgicalapp -p --authenticationDatabase surgical_outcomes
```

### SSL Certificate Issues

```bash
# Check certificate expiry
sudo certbot certificates

# Renew certificates
sudo certbot renew --force-renewal

# Restart Nginx
sudo systemctl restart nginx
```

## Performance Optimization

### 1. MongoDB Indexes

```bash
mongosh
use surgical_outcomes

# Create indexes
db.patients.createIndex({ "nhs_number": 1 }, { unique: true })
db.patients.createIndex({ "record_number": 1 }, { unique: true })
db.episodes.createIndex({ "patient_id": 1 })
db.treatments.createIndex({ "episode_id": 1 })
db.treatments.createIndex({ "treatment_date": -1 })
```

### 2. Nginx Caching

Add to Nginx config:
```nginx
# Cache zone definition
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=1g inactive=60m;

# In server block
location /api/reports/ {
    proxy_cache api_cache;
    proxy_cache_valid 200 5m;
    proxy_cache_key "$scheme$request_method$host$request_uri";
    add_header X-Cache-Status $upstream_cache_status;
    
    proxy_pass http://127.0.0.1:8000;
}
```

## Scaling Considerations

### Horizontal Scaling

1. **Load Balancer**: Use Nginx or HAProxy to distribute traffic
2. **Multiple Backend Instances**: Run multiple FastAPI instances
3. **MongoDB Replica Set**: For high availability
4. **Redis Session Store**: For shared sessions across instances

### Vertical Scaling

1. **Increase server resources**: More CPU/RAM
2. **Optimize database queries**: Add indexes
3. **Enable compression**: gzip in Nginx
4. **CDN**: Serve static assets via CDN

---

**Last Updated**: December 23, 2025  
**Version**: 1.0.0
