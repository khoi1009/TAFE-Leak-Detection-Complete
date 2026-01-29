# Deployment Guide

**Version:** 2.1.2 | **Updated:** January 29, 2026

---

## Prerequisites

### System Requirements

| Component | Requirement |
|-----------|-------------|
| **OS** | Windows 10+, macOS 10.15+, Ubuntu 18.04+ |
| **Python** | 3.9, 3.10, 3.11 |
| **RAM** | 4GB minimum, 8GB recommended |
| **Disk** | 500MB free (includes dependencies) |
| **Network** | Internal network or VPN access |

### Software Prerequisites

```bash
# Check Python version (3.9+)
python --version

# Check pip installed
pip --version

# Optional: Node.js for landing page (v18+)
node --version
npm --version
```

---

## Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/khoi1009/TAFE-Leak-Detection-Complete.git
cd TAFE-Leak-Detection-Complete
```

### Step 2: Create Environment File

**Copy template:**
```bash
cp .env.example .env
```

**Edit `.env` with production values:**
```env
# Backend
SECRET_KEY=generate-strong-key-here-min-32-chars
DATABASE_URL=sqlite+aiosqlite:///./leak_detection.db
DEBUG=false

# Frontend
API_URL=http://localhost:8000/api/v1
LOGIN_PORT=8050
DASHBOARD_PORT=8051
DEMO_MODE=false
```

**Generate SECRET_KEY (Linux/macOS):**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Generate SECRET_KEY (Windows PowerShell):**
```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 3: Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
cd ..
```

### Step 4: Install Frontend Dependencies

```bash
cd frontend
pip install -r requirements.txt
cd ..
```

### Step 5: Initialize Database

```bash
# This happens automatically on first run
# Or manually:
cd backend
python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"
cd ..
```

---

## Running the System

### Option 1: Full Automated Launch (Recommended)

**Windows:**
```powershell
.\start_all.bat
```

**Linux/macOS:**
```bash
chmod +x start_all.bat
bash start_all.bat
```

This starts 3 processes:
1. Backend API (:8000)
2. Login Portal (:8050)
3. Dashboard (:8051)

### Option 2: Manual Start (3 Terminals)

**Terminal 1 - Backend API:**
```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 - Login Portal:**
```bash
cd frontend
python login_app.py
```

**Terminal 3 - Dashboard:**
```bash
cd frontend
python app.py
```

### Option 3: Demo Mode (No Backend)

```bash
cd frontend
python app.py
# Access at http://localhost:8051 without authentication
```

### Option 4: Backend Only (API Development)

```bash
cd backend
uvicorn app.main:app --reload --port 8000
# Access API at http://localhost:8000/docs
```

---

## Access Points

### Development URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Landing Page | http://localhost:3000 | Marketing (Next.js, optional) |
| Login Portal | http://127.0.0.1:8050 | Authentication |
| Dashboard | http://127.0.0.1:8051 | Main UI |
| API Docs | http://127.0.0.1:8000/docs | Swagger UI |
| API Health | http://127.0.0.1:8000/health | Status check |

### Default Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Operator | `operator` | `operator123` |

---

## Configuration

### Backend Configuration (app/core/config.py)

```python
# Application
APP_NAME = "TAFE Leak Detection API"
APP_VERSION = "2.0.0"
DEBUG = True  # Set to False in production

# Server
HOST = "127.0.0.1"
PORT = 8000

# Security
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Database
DATABASE_URL = "sqlite+aiosqlite:///./leak_detection.db"

# CORS
CORS_ORIGINS = [
    "http://localhost:8050",
    "http://127.0.0.1:8050",
    "http://localhost:8051",
    "http://127.0.0.1:8051",
]
```

### Frontend Configuration (frontend/config.py)

```python
# API Settings
API_URL = "http://localhost:8000/api/v1"

# Port Settings
LOGIN_PORT = 8050
DASHBOARD_PORT = 8051

# Demo Mode
DEMO_MODE = False  # True = no authentication required

# Data Source
DATA_PATH = "data/demo_data.xlsx"  # Switch to production data when ready
```

### Data Source Configuration (config_leak_detection.yml)

```yaml
# Demo mode (5 properties, fast)
data_path: "data/demo_data.xlsx"

# Production mode (85 properties)
# data_path: "data_with_schools.xlsx"

# Update interval
update_interval: 300  # seconds

# ML threshold
alert_threshold: 70  # % confidence
```

---

## Environment Variables Reference

### Backend (.env)

```env
# Application
SECRET_KEY=your-super-secret-key-min-32-chars
DATABASE_URL=sqlite+aiosqlite:///./leak_detection.db
DEBUG=true

# Security
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Server
HOST=127.0.0.1
PORT=8000

# CORS (comma-separated)
CORS_ORIGINS=http://localhost:8050,http://localhost:8051

# Optional: Production database (PostgreSQL)
# DATABASE_URL=postgresql+asyncpg://user:password@host:5432/leak_detection
```

### Frontend (in app.py or config.py)

```python
# Set environment variables before running
import os
os.environ["API_URL"] = "http://localhost:8000/api/v1"
os.environ["LOGIN_PORT"] = "8050"
os.environ["DASHBOARD_PORT"] = "8051"
os.environ["DEMO_MODE"] = "false"
```

---

## Database Management

### Database Location

**Development:** `backend/leak_detection.db` (SQLite file)

### Backup Database

```bash
# Windows
copy backend\leak_detection.db backend\leak_detection.db.backup

# Linux/macOS
cp backend/leak_detection.db backend/leak_detection.db.backup
```

### Reset Database

```bash
# Windows
del backend\leak_detection.db

# Linux/macOS
rm backend/leak_detection.db

# Restart backend (auto-creates with default users)
```

### View Database

```bash
# Using sqlite3 CLI
sqlite3 backend/leak_detection.db

# Query users
sqlite> SELECT * FROM users;

# Query incidents
sqlite> SELECT * FROM incidents;

# Exit
sqlite> .quit
```

### Export Data

```bash
# Export users to CSV
sqlite3 backend/leak_detection.db ".headers on" ".mode csv" "SELECT * FROM users;" > users_export.csv

# Export incidents to CSV
sqlite3 backend/leak_detection.db ".headers on" ".mode csv" "SELECT * FROM incidents;" > incidents_export.csv
```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Update `SECRET_KEY` with production value
- [ ] Set `DEBUG=false`
- [ ] Update `CORS_ORIGINS` to production domains
- [ ] Configure production database (PostgreSQL recommended)
- [ ] Set up SSL/TLS certificates
- [ ] Configure logging (stdout to file)
- [ ] Set up monitoring/alerting
- [ ] Test with production data (85 schools)
- [ ] Performance test with concurrent users
- [ ] Backup strategy in place

### Gunicorn + Uvicorn (Linux/macOS)

```bash
# Install
pip install gunicorn

# Run with multiple workers
cd backend
gunicorn \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  app.main:app
```

### Docker Deployment (Optional)

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Backend
COPY backend/requirements.txt ./backend/
RUN pip install -r backend/requirements.txt

# Frontend
COPY frontend/requirements.txt ./frontend/
RUN pip install -r frontend/requirements.txt

COPY . .

EXPOSE 8000 8050 8051

CMD ["bash", "start_all.bat"]
```

**Build & Run:**
```bash
docker build -t waterwatch:2.1.2 .
docker run -p 8000:8000 -p 8050:8050 -p 8051:8051 waterwatch:2.1.2
```

### Nginx Reverse Proxy

```nginx
upstream backend {
    server 127.0.0.1:8000;
}

upstream frontend_login {
    server 127.0.0.1:8050;
}

upstream frontend_dashboard {
    server 127.0.0.1:8051;
}

server {
    listen 443 ssl http2;
    server_name waterwatch.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Dashboard
    location /dashboard {
        proxy_pass http://frontend_dashboard;
    }

    # Login
    location /login {
        proxy_pass http://frontend_login;
    }
}
```

---

## Monitoring & Health Checks

### Health Check Endpoint

```bash
# Check backend status
curl http://127.0.0.1:8000/health

# Response:
# {"status": "healthy"}
```

### Monitoring Script

```bash
#!/bin/bash
# monitor.sh

while true; do
    echo "=== $(date) ==="

    # Check API
    api_status=$(curl -s http://127.0.0.1:8000/health | jq -r '.status')
    echo "API Status: $api_status"

    # Check database
    db_count=$(sqlite3 backend/leak_detection.db "SELECT COUNT(*) FROM incidents;")
    echo "Incidents in DB: $db_count"

    # Check processes
    ps aux | grep -E "uvicorn|python" | grep -v grep

    sleep 60
done
```

**Run monitoring:**
```bash
chmod +x monitor.sh
./monitor.sh
```

### Log Monitoring

**Backend logs (stderr):**
```bash
cd backend
uvicorn app.main:app --reload 2>&1 | tee api.log
```

**Watch logs in real-time:**
```bash
tail -f backend/api.log
```

---

## Troubleshooting

### Issue: "Address already in use"

**Cause:** Port already bound by another process

**Solution:**
```bash
# Windows - Find process on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/macOS
lsof -i :8000
kill -9 <PID>
```

### Issue: "Connection refused" from dashboard to API

**Cause:** API not running or CORS misconfigured

**Solution:**
```bash
# Check if API running
curl http://127.0.0.1:8000/health

# Verify CORS in config.py
CORS_ORIGINS = ["http://localhost:8050", "http://localhost:8051"]

# Restart backend with correct origin
```

### Issue: "Database is locked"

**Cause:** Multiple processes accessing SQLite simultaneously

**Solution:**
```bash
# Switch to PostgreSQL in production
DATABASE_URL=postgresql+asyncpg://user:pass@host/db

# Or: Restart backend to release lock
```

### Issue: "No such table: users"

**Cause:** Database not initialized

**Solution:**
```bash
# Delete database
cd backend
rm leak_detection.db

# Restart backend (auto-creates schema)
cd ..
python backend/app/main.py
```

### Issue: "ImportError: No module named 'fastapi'"

**Cause:** Dependencies not installed

**Solution:**
```bash
cd backend
pip install -r requirements.txt
```

### Issue: "TokenExpired" or "InvalidToken"

**Cause:** JWT token expired or invalid

**Solution:**
```bash
# Refresh token
curl -X POST http://127.0.0.1:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"your_refresh_token"}'

# Or: Re-login
```

---

## Performance Tuning

### Database Optimization

```sql
-- Create indexes for common queries
CREATE INDEX idx_incidents_status ON incidents(status);
CREATE INDEX idx_incidents_school_name ON incidents(school_name);
CREATE INDEX idx_incidents_created_at ON incidents(created_at DESC);
CREATE INDEX idx_users_email ON users(email);
```

### API Optimization

```python
# Enable query result caching
from functools import lru_cache

@lru_cache(maxsize=128)
def get_schools():
    """Cache static school data."""
    pass

# Use pagination for large result sets
@router.get("/incidents/")
async def list_incidents(skip: int = 0, limit: int = 10):
    # Limit default to 10, max 100
    limit = min(limit, 100)
    pass
```

### Dashboard Optimization

```python
# Reduce refresh frequency
UPDATE_INTERVAL = 300  # 5 minutes instead of 30 seconds

# Cache expensive computations
stats_cache = {}

# Lazy load tabs (only compute visible tab)
```

---

## Backup & Disaster Recovery

### Backup Strategy

```bash
#!/bin/bash
# daily_backup.sh

BACKUP_DIR="/backups/waterwatch"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
cp backend/leak_detection.db $BACKUP_DIR/leak_detection_$DATE.db

# Backup configuration
cp .env $BACKUP_DIR/env_$DATE

# Backup false alarm patterns
cp frontend/False_Alarm_Patterns.csv $BACKUP_DIR/patterns_$DATE.csv

# Compress
tar -czf $BACKUP_DIR/backup_$DATE.tar.gz $BACKUP_DIR/

# Cleanup old backups (>30 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "✅ Backup completed: $BACKUP_DIR/backup_$DATE.tar.gz"
```

**Schedule with cron (Linux/macOS):**
```bash
# Daily at 2 AM
0 2 * * * /path/to/daily_backup.sh
```

**Schedule with Task Scheduler (Windows):**
```
Program: C:\Python39\python.exe
Arguments: C:\path\to\daily_backup.py
Time: Daily at 2:00 AM
```

### Recovery

```bash
# Restore from backup
tar -xzf /backups/waterwatch/backup_20260129_020000.tar.gz
cp /backups/waterwatch/leak_detection_20260129_020000.db backend/leak_detection.db

# Restart backend
```

---

## Security Hardening

### Change Default Credentials

```bash
# Login as admin with default password
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@tafe.nsw.edu.au","password":"admin123"}'

# Change password via API (when implemented)
# Or manually update in database:
sqlite3 backend/leak_detection.db
UPDATE users SET hashed_password='<new_hash>' WHERE username='admin';
```

### Rotate SECRET_KEY

1. Generate new key
2. Update `.env`
3. All existing tokens become invalid
4. Users must re-login

### HTTPS in Production

```python
# Use HTTPS URLs only
CORS_ORIGINS = ["https://waterwatch.example.com"]

# In nginx:
listen 443 ssl http2;
ssl_certificate /path/to/cert.pem;
ssl_certificate_key /path/to/key.pem;
```

---

## Maintenance

### Regular Tasks

**Daily:**
- [ ] Monitor health checks
- [ ] Review error logs
- [ ] Check disk space

**Weekly:**
- [ ] Backup database
- [ ] Review incident statistics
- [ ] Check false alarm patterns

**Monthly:**
- [ ] Update dependencies (`pip list --outdated`)
- [ ] Review security patches
- [ ] Performance analysis

**Quarterly:**
- [ ] Database optimization (rebuild indexes)
- [ ] Archive old incidents (>12 months)
- [ ] Update documentation

---

## Related Documentation

- [System Architecture](./system-architecture.md) - Technical design
- [Code Standards](./code-standards.md) - Development guidelines
- [Project Overview](./project-overview-pdr.md) - Requirements & goals
