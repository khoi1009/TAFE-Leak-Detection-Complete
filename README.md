# TAFE Leak Detection - Complete Edition 🌊

A comprehensive water leak detection system for NSW schools featuring:

- **FastAPI Backend** with JWT authentication
- **Dash Frontend** with UI UX Pro Max design
- **GIS Map Integration** with interactive school locations
- **Real-time Simulation** with ML-based anomaly detection

## 🚀 Quick Start

### Option 1: Full System (Recommended)

```powershell
# Double-click or run:
.\start_all.bat
```

This starts all 3 services automatically:

- Backend API (port 8000)
- Login Portal (port 8050)
- Dashboard (port 8051)

### Option 2: Demo Mode (No Backend)

```powershell
.\start_demo.bat
```

Runs dashboard on port 8050 without authentication.

### Option 3: Manual Start

```powershell
# Terminal 1 - Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2 - Dashboard
cd frontend
pip install -r requirements.txt
python app.py

# Terminal 3 - Login Portal (optional)
cd frontend
python login_app.py
```

## 🔐 Default Credentials

| Role     | Username | Password    |
| -------- | -------- | ----------- |
| Admin    | admin    | admin123    |
| Operator | operator | operator123 |

## 📁 Project Structure

```
TAFE-Leak-Detection-Complete/
│
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── api/               # API endpoints
│   │   │   ├── auth.py        # Authentication
│   │   │   ├── incidents.py   # Incident management
│   │   │   └── schools.py     # GIS data
│   │   ├── core/              # Core utilities
│   │   │   ├── config.py      # Settings
│   │   │   ├── database.py    # SQLAlchemy async
│   │   │   └── security.py    # JWT, passwords
│   │   ├── models/            # Database models
│   │   │   ├── user.py        # User model
│   │   │   └── incident.py    # Incident model
│   │   └── main.py            # FastAPI app
│   └── requirements.txt
│
├── frontend/                   # Dash Dashboard
│   ├── assets/                # CSS styling
│   │   ├── design-system.css  # UI UX Pro Max
│   │   └── responsive.css     # Mobile support
│   ├── data/                  # Demo data
│   │   ├── demo_data.xlsx     # Water consumption
│   │   ├── demo_school_mapping.csv
│   │   └── demo_schools_gis.json
│   ├── app.py                 # Main dashboard
│   ├── login_app.py           # Login portal
│   ├── callbacks.py           # Dash callbacks
│   ├── components.py          # UI components
│   ├── components_map.py      # GIS Map component
│   ├── layout.py              # Dashboard layout
│   ├── config.py              # Configuration
│   ├── data.py                # Data loading
│   ├── processing.py          # Data processing
│   ├── utils.py               # Utilities
│   ├── Model_1_realtime_simulation.py  # ML engine
│   ├── engine_fallback.py     # Demo engine
│   └── false_alarm_patterns.py
│
├── start_all.bat              # Start everything
├── start_backend.bat          # Start API only
├── start_dashboard.bat        # Start dashboard only
├── start_login.bat            # Start login only
├── start_demo.bat             # Demo mode (no auth)
└── README.md
```

## 🌐 Access Points

| Service      | URL                          | Description         |
| ------------ | ---------------------------- | ------------------- |
| Login Portal | http://127.0.0.1:8050        | Authentication page |
| Dashboard    | http://127.0.0.1:8051        | Main dashboard      |
| API Docs     | http://127.0.0.1:8000/docs   | Swagger UI          |
| API Health   | http://127.0.0.1:8000/health | Health check        |

## ✨ Features

### 🔍 Leak Detection Engine

- Multi-signal analysis: MNF, RESIDUAL, CUSUM, AFTERHRS, BURSTBF
- Confidence scoring: 0-100% leak probability
- Day-by-day replay simulation
- False alarm pattern learning

### 🗺️ GIS Map Integration

- Interactive NSW map with 50 demo schools
- Toggle: "All Schools" vs "Leak Alerts Only"
- Color-coded status markers
- Click for school details

### 📊 Dashboard Tabs

1. **Overview** - KPIs, summary charts
2. **Events** - Incident cards with details
3. **Log** - Action history
4. **GIS Map** - Interactive map

### 🎯 Action Workflows

- Acknowledge, Watch, Escalate, Resolve, Ignore
- Assignment to team members
- Cost tracking and notes

### 🔐 Authentication

- JWT-based authentication
- Role-based access (admin, operator, viewer)
- Session management
- Secure password hashing (bcrypt)

## 🛠️ Configuration

### Environment Variables

```env
# Backend
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite+aiosqlite:///./leak_detection.db
DEBUG=true

# Frontend
API_URL=http://localhost:8000/api/v1
LOGIN_PORT=8050
DASHBOARD_PORT=8051
DEMO_MODE=false
```

### Demo vs Production Data

Edit `frontend/config_leak_detection.yml`:

```yaml
# Demo mode (fast - 5 properties)
data_path: "data/demo_data.xlsx"
# Production (85 properties)
# data_path: "data_with_schools.xlsx"
```

## 📈 API Endpoints

### Authentication

```
POST /api/v1/auth/login     - Login
POST /api/v1/auth/register  - Register
POST /api/v1/auth/refresh   - Refresh token
GET  /api/v1/auth/me        - Current user
```

### Incidents

```
GET  /api/v1/incidents/      - List incidents
GET  /api/v1/incidents/stats - Statistics
POST /api/v1/incidents/      - Create incident
PATCH /api/v1/incidents/{id} - Update incident
```

### Schools

```
GET /api/v1/schools/        - List schools
GET /api/v1/schools/search  - Search schools
GET /api/v1/schools/alerts  - Schools with alerts
```

## 🔧 Development

### Run Tests

```powershell
cd backend
pytest

cd frontend
python test_pattern_matching.py
```

### Database Reset

```powershell
cd backend
del leak_detection.db
# Restart backend - creates fresh DB
```

## 📝 Changelog

### v2.0.0 - Complete Edition (December 2025)

- ✅ Combined Dashboard + Production repos
- ✅ FastAPI backend with Pydantic v2 compatibility
- ✅ JWT authentication system
- ✅ GIS Map with school locations
- ✅ Demo mode without backend
- ✅ Unified startup scripts

### v1.0.0 - Initial Release

- ✅ Modular dashboard architecture
- ✅ UI UX Pro Max design
- ✅ Leak detection engine

## 👥 Contributors

- **TAFE NSW** - Project sponsor
- **Griffith University** - Research partnership
- **GitHub Copilot** - Development assistance

## 📄 License

Proprietary - TAFE NSW / Griffith University

---

**GitHub Repository:** https://github.com/khoi1009/TAFE-Leak-Detection-Complete

Last Updated: December 6, 2025
