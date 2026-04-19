#!/bin/bash
set -e

echo "=== Email Finder Setup ==="

APP_DIR=$(pwd)
APP_USER=$(whoami)
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)"
   exit 1
fi

echo "Step 1: Installing system dependencies..."
apt-get update
apt-get install -y python3.12 python3.12-venv python3-pip nodejs npm redis-server nginx git

echo "Step 2: Setting up Python virtual environment..."
cd "$BACKEND_DIR"
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Step 3: Initializing database..."
python -c "from app.core.database import create_db_and_tables; create_db_and_tables()"

echo "Step 4: Building frontend..."
cd "$FRONTEND_DIR"
npm install
npm run build

echo "Step 5: Creating systemd services..."

# Backend service
cat > /etc/systemd/system/email-finder-backend.service << EOF
[Unit]
Description=Email Finder Backend
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/venv/bin"
ExecStart=$BACKEND_DIR/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Worker service
cat > /etc/systemd/system/email-finder-worker.service << EOF
[Unit]
Description=Email Finder ARQ Worker
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/venv/bin"
ExecStart=$BACKEND_DIR/venv/bin/arq app.workers.tasks.WorkerSettings
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "Step 6: Configuring Nginx..."

# Backup existing Nginx config if it exists
if [ -f /etc/nginx/sites-available/default ]; then
    cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.bak
fi

cat > /etc/nginx/sites-available/default << 'NGINX_EOF'
# HTTP redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name _;
    return 301 https://$host$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name findymail.aprexio.com;

    ssl_certificate /etc/letsencrypt/live/findymail.aprexio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/findymail.aprexio.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    client_max_body_size 10m;

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # Frontend static files
    location / {
        root FRONTEND_DIST_DIR;
        try_files $uri $uri/ /index.html;
    }
}
NGINX_EOF

# Replace placeholder with actual path
sed -i "s|FRONTEND_DIST_DIR|$FRONTEND_DIR/dist|g" /etc/nginx/sites-available/default

# Test Nginx config
nginx -t

echo "Step 7: Enabling and starting services..."
systemctl daemon-reload
systemctl enable redis-server email-finder-backend email-finder-worker nginx
systemctl restart redis-server
systemctl restart email-finder-backend
systemctl restart email-finder-worker
systemctl restart nginx

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Services status:"
systemctl status email-finder-backend --no-pager
systemctl status email-finder-worker --no-pager
systemctl status redis-server --no-pager
systemctl status nginx --no-pager
echo ""
echo "View logs:"
echo "  Backend:  sudo journalctl -u email-finder-backend -f"
echo "  Worker:   sudo journalctl -u email-finder-worker -f"
echo "  Nginx:    sudo journalctl -u nginx -f"
echo ""
echo "Access your app at: https://findymail.aprexio.com"
echo ""
