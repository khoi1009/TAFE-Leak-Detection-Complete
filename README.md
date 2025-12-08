# TAFE Leak Detection - Complete Edition 🌊

> **WaterWatch** - Intelligent Water Leak Detection for NSW Government Assets

A comprehensive water leak detection system for NSW schools featuring:

- **Landing Page** - Modern Next.js marketing page with Tailwind CSS
- **Login Portal** - Deep Ocean themed authentication with Glassmorphism UI
- **FastAPI Backend** with JWT authentication
- **Dash Dashboard** with UI UX Pro Max design
- **GIS Map Integration** with interactive school locations
- **Real-time Simulation** with ML-based anomaly detection

## 🎨 Design Theme

The system uses a **"Deep Ocean Data"** aesthetic:

- 🌊 Navy blue gradient backgrounds with bioluminescent cyan glows
- 💧 Glassmorphism card effects with backdrop blur
- ✨ Hydro-Pulse loading animations
- 🎬 Smooth transitions and floating elements

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

### Option 3: With Landing Page

```powershell
# Terminal 1 - Landing Page (requires Node.js)
cd ../AQUA-GOV-Landing-Page/src/aqua-gov-app
npm run dev
# Opens at http://localhost:3000

# Terminal 2 - Login + Dashboard
.\start_all.bat
```

### Option 4: Manual Start

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
│   │   ├── login-styles.css   # Login page styles (Deep Ocean theme)
│   │   ├── _design-system.css # Dashboard UI UX Pro Max
│   │   └── _responsive.css    # Mobile support
│   ├── data/                  # Demo data
│   │   ├── demo_data.xlsx     # Water consumption
│   │   ├── demo_school_mapping.csv
│   │   └── demo_schools_gis.json
│   ├── app.py                 # Main dashboard
│   ├── login_app.py           # Login portal (WaterWatch themed)
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

| Service      | URL                          | Description               |
| ------------ | ---------------------------- | ------------------------- |
| Landing Page | http://localhost:3000        | Marketing page (Next.js)  |
| Login Portal | http://127.0.0.1:8050        | WaterWatch authentication |
| Dashboard    | http://127.0.0.1:8051        | Main dashboard            |
| API Docs     | http://127.0.0.1:8000/docs   | Swagger UI                |
| API Health   | http://127.0.0.1:8000/health | Health check              |

## ✨ Features

### 🎨 Login Portal (WaterWatch Theme)

- **Deep Ocean Background** - Animated navy/cyan gradients with bioluminescent glows
- **Glassmorphism Card** - Frosted glass effect with shimmer border animation
- **Hydro-Pulse Loader** - Water ripple animation during authentication
- **Compact Form** - 300px width for clean, focused input

### 🌐 Landing Page (Next.js)

- **Hero Section** - Bold tagline with animated water droplet
- **Problem/Solution** - Clear value proposition
- **Feature Highlights** - AI detection, real-time monitoring, cost savings
- **Statistics** - Impact numbers with animated counters
- **Demo Access** - Direct links to login portal
- **Responsive** - Mobile-first design with Tailwind CSS

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

### v2.1.0 - WaterWatch Edition (December 2025)

- ✅ Rebranded from "AQUA-GOV" to **WaterWatch**
- ✅ New **Deep Ocean Data** login theme
  - Animated gradient background with bioluminescent glows
  - Glassmorphism card with shimmer border
  - Hydro-Pulse loading spinner
  - Compact 300px form width
- ✅ Created Next.js **Landing Page** (localhost:3000)
  - Hero, Features, Statistics, Demo Access sections
  - Tailwind CSS styling
  - Links to Login Portal
- ✅ Separated CSS for Login vs Dashboard
  - `login-styles.css` - Deep Ocean theme
  - `_design-system.css` - Dashboard theme (prefixed to avoid auto-load)

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

## 🎨 Related Projects

### WaterWatch Landing Page

Located at: `../AQUA-GOV-Landing-Page/src/aqua-gov-app/`

```powershell
# To run the landing page
cd ../AQUA-GOV-Landing-Page/src/aqua-gov-app
npm install
npm run dev
```

**Tech Stack:** Next.js 13.5.6, React 18, Tailwind CSS 3

## 👥 Contributors

- **TAFE NSW** - Project sponsor
- **Griffith University** - Research partnership
- **GitHub Copilot** - Development assistance

## 📄 License

Proprietary - TAFE NSW / Griffith University

---

**GitHub Repository:** https://github.com/khoi1009/TAFE-Leak-Detection-Complete

Last Updated: December 8, 2025
