# Email Finder Deployment Documentation

## Summary
This document covers the deployment journey of Email Finder from Docker-based setup to a systemd-based VPS deployment with custom domain and HTTPS.

---

## Initial Decisions

### 1. **Docker → Systemd Migration**
- **Decision:** Move away from Docker to direct systemd services
- **Reason:** Simpler debugging, easier management on a single-user VPS, reduced complexity
- **Trade-off:** Lost containerization benefits but gained operational simplicity

### 2. **PostgreSQL → SQLite**
- **Decision:** Switch database from PostgreSQL to SQLite
- **Reason:** Single-user tool with 2-3k lookups/week doesn't need a dedicated database server
- **Benefits:** 
  - Zero setup required
  - No separate database process to manage
  - File-based database easier to backup
  - Perfect for VPS deployment
- **Change:** JSONB (PostgreSQL) → JSON (SQLite compatible)

### 3. **Vite Preview → Static File Serving**
- **Decision:** Build frontend once and serve static files via Nginx
- **Reason:** Vite preview/dev server has security checks that block production domains
- **Solution:** 
  - Build frontend with `npm run build`
  - Serve `/dist` folder via Nginx with `try_files` for SPA routing
  - No separate Node process needed

### 4. **Custom Domain Setup**
- **Domain:** findymail.aprexio.com (changed from findemail.aprexio.com)
- **DNS:** DigitalOcean DNS management
- **HTTPS:** Let's Encrypt with Certbot
- **Reverse Proxy:** Nginx routing `/api/*` to backend, `/*` to static frontend

---

## Problems Faced & Solutions

### Problem 1: JSONB Type Not Supported in SQLite
**Error:** `SQLiteTypeCompiler can't render element of type JSONB`

**Root Cause:** PostgreSQL's JSONB type doesn't exist in SQLite

**Solution:** Changed `domain_pattern.py` to use `JSON` type instead
```python
# Before
from sqlalchemy.dialects.postgresql import JSONB
sa_column=Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))

# After
from sqlalchemy import JSON
sa_column=Column(JSON, nullable=False)
```

**Files Modified:** `backend/app/models/domain_pattern.py`

---

### Problem 2: Systemd Service Timeout
**Error:** `email-finder-backend.service: start operation timed out`

**Root Cause:** Service type was `Type=notify`, which waits for a systemd readiness signal that Uvicorn doesn't send

**Solution:** Changed service type to `Type=simple`
```ini
# Before
[Service]
Type=notify

# After
[Service]
Type=simple
```

**Files Modified:** `setup.sh`

---

### Problem 3: Docker-Proxy Holding Ports
**Error:** `bind() to 0.0.0.0:80 failed (98: Address already in use)`

**Root Cause:** Old Docker containers still running, their proxy processes holding ports 80/443

**Solution:** 
```bash
docker compose down
docker system prune -f
sudo killall docker-proxy
```

---

### Problem 4: Vite Security Blocking Production Domain
**Error:** Browser shows "Blocked request. This host is not allowed" with reference to vite.config.js

**Root Cause:** Vite preview server (used in original Docker setup) validates allowed hosts

**Solution:** Switch to serving pre-built static files instead of running Vite server
- Frontend Dockerfile changed to use `serve` package instead of `npm run preview`
- Nginx serves `/frontend/dist` directly
- No runtime Vite server needed

**Files Modified:** `frontend/Dockerfile`, `setup.sh` Nginx config

---

### Problem 5: Current Issue - Still Getting Vite Error After Migration
**Status:** Investigating

**Symptoms:**
- Nginx config looks correct (serves static files)
- Frontend dist folder exists with proper index.html
- curl returns Vite error message
- Nginx access logs empty

**Possible Causes:**
- Nginx config not being reloaded properly
- Path permissions issue
- Still pointing to old frontend somewhere
- Nginx config syntax issue with SSL certificates

**Next Steps to Debug:**
1. Verify nginx is actually serving the dist folder
2. Check file permissions on /root/email-finder/frontend/dist/
3. Test if HTML is being served at all vs error page
4. Check if SSL cert paths are correct

---

## System Architecture

### Services Running
```
┌─────────────────────────────────────────────────┐
│         Nginx (Reverse Proxy)                   │
│    Listening on port 80 (→443) and 443         │
└──────────────┬──────────────────────────────────┘
               │
      ┌────────┴────────┐
      │                 │
      ▼                 ▼
┌──────────────┐  ┌──────────────────┐
│  Backend     │  │  Frontend        │
│ :8000        │  │  /dist (static)  │
│ (FastAPI)    │  │                  │
└──────┬───────┘  └──────────────────┘
       │
       ├─── Redis (:6379)
       ├─── SQLite (email_finder.db)
       └─── ARQ Worker (processes jobs)
```

### Systemd Services
- `email-finder-backend.service` - FastAPI server
- `email-finder-worker.service` - ARQ job processor
- `nginx.service` - Web server
- `redis-server.service` - Cache/queue

---

## Configuration Files Created

### 1. `backend/app/core/config.py`
- Changed default `DATABASE_URL` to `sqlite:///./email_finder.db`
- Added SQLite-specific connection handling

### 2. `backend/app/core/database.py`
- Added SQLite detection and configuration
- Enabled foreign keys with PRAGMA
- Removed PostgreSQL-specific pool settings for SQLite

### 3. `backend/app/models/domain_pattern.py`
- Replaced JSONB with JSON type
- Removed server_default for SQLite compatibility

### 4. `frontend/Dockerfile`
- Changed from multi-stage build with Vite preview
- Now builds frontend and serves with `serve` package
- Uses lightweight static file server

### 5. `frontend/vite.config.ts`
- Simplified config (removed allowedHosts settings that didn't help)
- Kept basic dev server config

### 6. `setup.sh`
- Comprehensive setup script that:
  - Installs system dependencies (Python 3.12, Node, Redis, Nginx)
  - Creates Python venv and installs dependencies
  - Initializes SQLite database
  - Builds frontend
  - Creates 2 systemd service files
  - Configures Nginx with SSL
  - Starts all services

### 7. `/etc/systemd/system/email-finder-backend.service`
```ini
[Unit]
Description=Email Finder Backend
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/email-finder/backend
Environment="PATH=/root/email-finder/backend/venv/bin"
ExecStart=/root/email-finder/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 8. `/etc/nginx/sites-available/default`
```nginx
# HTTP → HTTPS redirect
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

    # API proxy to backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static frontend files
    location / {
        root /root/email-finder/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
}
```

---

## Environment Changes

### `.env.example` Updated
```bash
# Old (PostgreSQL)
DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/email_finder

# New (SQLite)
DATABASE_URL=sqlite:///./email_finder.db

# Old (Docker Redis)
REDIS_URL=redis://redis:6379/0

# New (localhost Redis)
REDIS_URL=redis://localhost:6379/0
```

---

## Deployment Steps Completed

1. ✅ Created setup.sh script
2. ✅ Updated database config for SQLite
3. ✅ Modified domain_pattern model for SQLite JSON type
4. ✅ Fixed systemd service type (Type=simple)
5. ✅ Updated frontend to build static files
6. ✅ Set up Nginx with SSL/HTTPS
7. ✅ Created DNS records pointing to droplet
8. ✅ Obtained Let's Encrypt certificate
9. ✅ Started backend, worker, redis services
10. ⚠️ Frontend serving - currently investigating issue

---

## Current Status

### Working ✅
- Backend FastAPI server running on :8000
- ARQ worker processing jobs
- Redis cache/queue operational
- Nginx reverse proxy listening on 80/443
- SSL certificate installed and valid
- Database initialized with SQLite

### In Progress ⚠️
- Frontend static file serving (Vite error still appearing)
- Need to debug why Nginx isn't serving index.html properly

---

## How to Debug the Current Issue

```bash
# 1. Check service status
sudo systemctl status email-finder-backend email-finder-worker nginx

# 2. View logs
sudo journalctl -u email-finder-backend -f
sudo journalctl -u nginx -f

# 3. Test backend API
curl https://findymail.aprexio.com/api/health -k

# 4. Check file permissions
ls -la /root/email-finder/frontend/dist/
sudo -u www-data test -r /root/email-finder/frontend/dist/index.html && echo "readable" || echo "not readable"

# 5. Test Nginx serving file
curl -v https://findymail.aprexio.com/ -k

# 6. Verify Nginx config
sudo nginx -t
sudo cat /etc/nginx/sites-enabled/default

# 7. Check what processes are listening
sudo lsof -i :80,443
sudo netstat -tlnp | grep -E ':80|:443'
```

---

## Next Steps

1. **Fix Frontend Serving**
   - Debug why static files aren't being served
   - Possible fix: change Nginx root path or permissions
   - Alternative: serve frontend through backend as fallback

2. **Test Full Workflow**
   - Login with APP_PASSWORD
   - Run test lookups
   - Verify all features work

3. **Monitoring & Logging**
   - Set up log rotation for journalctl
   - Create monitoring script for service health

4. **Backups**
   - Set up automated SQLite backup
   - Document backup restore procedure

---

## Key Learnings

1. **Vite Security:** Vite preview server validates allowed hosts - for production, always build and serve static files
2. **SystemD Service Types:** `Type=notify` requires explicit readiness signal; use `Type=simple` for standard servers
3. **Docker Cleanup:** Always fully remove Docker containers when switching to native services; proxy processes can hang around
4. **SQLite for Small Tools:** Perfect for single-user VPS tools; JSONB → JSON change minimal
5. **Nginx Static Serving:** Use `root` + `try_files $uri $uri/ /index.html` for SPA routing

---

## Files Modified/Created

```
Email Finder/
├── .env.example (modified)
├── DEPLOYMENT.md (NEW - this file)
├── setup.sh (NEW)
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py (modified)
│   │   │   └── database.py (modified)
│   │   └── models/
│   │       └── domain_pattern.py (modified)
│   └── Dockerfile (removed - using systemd instead)
├── frontend/
│   ├── Dockerfile (modified - now serves static files)
│   └── vite.config.ts (modified)
├── docker-compose.yml (removed - using systemd)
└── nginx/ (config now in /etc/nginx/)
```

