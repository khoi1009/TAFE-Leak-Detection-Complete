# Codebase Summary

**Generated:** January 29, 2026 | **Total LOC:** ~15,500 | **Version:** 2.1.2

---

## Project Structure

```
TAFE-Leak-Detection-Complete/
│
├── backend/                          # FastAPI REST API (903 LOC)
│   ├── app/
│   │   ├── api/                     # Route handlers
│   │   │   ├── auth.py              # Auth endpoints (register, login, refresh)
│   │   │   ├── incidents.py         # Incident CRUD & statistics
│   │   │   ├── schools.py           # School listing & GIS search
│   │   │   └── __init__.py          # Router aggregation
│   │   ├── core/                    # Core utilities
│   │   │   ├── config.py            # Pydantic settings & env vars
│   │   │   ├── database.py          # SQLAlchemy async setup
│   │   │   ├── security.py          # JWT, password hashing, auth deps
│   │   │   └── __init__.py
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   │   ├── user.py              # User model + roles enum
│   │   │   ├── incident.py          # Incident model + status enum
│   │   │   └── __init__.py
│   │   ├── services/                # Business logic (stub)
│   │   │   └── __init__.py
│   │   ├── main.py                  # FastAPI app entry (112 LOC)
│   │   └── __init__.py
│   ├── requirements.txt             # Python dependencies
│   └── leak_detection.db            # SQLite database (auto-created)
│
├── frontend/                         # Dash Dashboard (12,207 LOC)
│   ├── app.py                       # Main Dash app entry
│   ├── login_app.py                 # Login portal (844 LOC, Deep Ocean theme)
│   ├── callbacks.py                 # Dash callbacks (2,323 LOC)
│   ├── layout.py                    # Dashboard UI structure (2,095 LOC)
│   ├── components.py                # Reusable UI components
│   ├── components_map.py            # GIS map component (1,662 LOC)
│   ├── data.py                      # Data loading & caching
│   ├── processing.py                # Data transformations
│   ├── utils.py                     # Helper functions
│   ├── config.py                    # Frontend settings
│   ├── Model_1_realtime_simulation.py  # ML engine (2,206 LOC)
│   ├── engine_fallback.py           # Demo fallback (no ML)
│   ├── false_alarm_patterns.py      # Pattern learning module
│   ├── requirements.txt             # Python dependencies
│   ├── assets/
│   │   ├── login-styles.css         # Login page styling (Deep Ocean)
│   │   ├── _design-system.css       # Dashboard theme (UI UX Pro Max)
│   │   └── _responsive.css          # Mobile responsive styles
│   ├── data/
│   │   ├── demo_data.xlsx           # 5-property sample data
│   │   ├── demo_school_mapping.csv  # School IDs
│   │   └── demo_schools_gis.json    # GIS coordinates (50 schools)
│   ├── config_leak_detection.yml    # Data path config
│   └── False_Alarm_Patterns.csv     # Learned patterns (auto-generated)
│
├── .claude/                         # Claude development config
│   ├── rules/                       # Development guidelines
│   ├── scripts/                     # Utility scripts
│   └── skills/                      # Skill implementations
│
├── plans/                           # Project planning & reports
│   └── reports/                     # Generated documentation
│
├── start_all.bat                    # Launch all services
├── start_backend.bat                # Launch backend only
├── start_dashboard.bat              # Launch dashboard only
├── start_login.bat                  # Launch login portal only
├── start_demo.bat                   # Demo mode (no auth)
├── start_waterwatch_demo.bat        # WaterWatch demo launcher
│
├── README.md                        # User guide & quick start
├── .env.example                     # Environment template
├── .gitignore                       # Git exclusions
├── CLAUDE.md                        # AI development guidelines
└── docs/                            # Documentation (this directory)
    ├── project-overview-pdr.md
    ├── codebase-summary.md          # YOU ARE HERE
    ├── code-standards.md
    ├── system-architecture.md
    ├── project-roadmap.md
    └── deployment-guide.md
```

---

## Backend Architecture

### Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **fastapi** | 0.109+ | Web framework & routing |
| **uvicorn** | 0.25+ | ASGI server |
| **sqlalchemy** | 2.0+ | ORM (async-compatible) |
| **aiosqlite** | 0.19+ | Async SQLite driver |
| **python-jose** | 3.3+ | JWT signing/verification |
| **passlib+bcrypt** | 1.7.4+ | Password hashing |
| **pydantic** | 2.0+ | Request validation |

### Key Files

| File | LOC | Responsibility |
|------|-----|-----------------|
| `main.py` | 112 | App initialization, lifespan, default users |
| `auth.py` | 168 | Auth endpoints, token generation, user ops |
| `incidents.py` | 182 | Incident CRUD, filtering, pagination, stats |
| `schools.py` | ~80 | School listing, search, alert filtering |
| `user.py` | 45 | User model + role enum (4 roles) |
| `incident.py` | ~60 | Incident model + status enum (6 statuses) |
| `config.py` | 48 | Settings from .env, CORS config |
| `database.py` | ~40 | Async engine, session, Base class |
| `security.py` | ~80 | Token creation, verification, password ops |

### Database Schema

#### Users Table
```sql
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  username VARCHAR(50) UNIQUE NOT NULL,
  hashed_password VARCHAR(255) NOT NULL,
  full_name VARCHAR(100),
  role VARCHAR(20) DEFAULT 'viewer',
  is_active BOOLEAN DEFAULT TRUE,
  created_at DATETIME,
  updated_at DATETIME,
  last_login DATETIME
);
```

#### Incidents Table
```sql
CREATE TABLE incidents (
  id INTEGER PRIMARY KEY,
  property_id VARCHAR(100) NOT NULL,
  school_name VARCHAR(255) NOT NULL,
  confidence FLOAT NOT NULL,
  signals JSON,  -- {MNF: 0.4, RESIDUAL: 0.2, ...}
  status VARCHAR(20) DEFAULT 'open',
  assigned_to INTEGER,
  cost_estimate FLOAT,
  notes TEXT,
  created_at DATETIME,
  updated_at DATETIME,
  FOREIGN KEY (assigned_to) REFERENCES users(id)
);
```

### API Endpoints

**Base URL:** `http://localhost:8000/api/v1`

#### Auth
- `POST /auth/register` - Create user
- `POST /auth/login` - Get tokens
- `POST /auth/refresh` - Refresh access token
- `GET /auth/me` - Current user info
- `POST /auth/logout` - Invalidate token

#### Incidents
- `GET /incidents/` - List incidents (pagination, filter, sort)
- `GET /incidents/stats` - Summary statistics
- `POST /incidents/` - Create incident
- `GET /incidents/{id}` - Get single incident
- `PATCH /incidents/{id}` - Update incident (status, assignment, notes)
- `DELETE /incidents/{id}` - Archive incident

#### Schools
- `GET /schools/` - List all schools
- `GET /schools/search` - Search by name/location
- `GET /schools/alerts` - Schools with active alerts

---

## Frontend Architecture

### Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **dash** | Latest | Interactive web framework |
| **plotly** | Latest | Interactive visualizations |
| **pandas** | Latest | Data manipulation |
| **numpy** | Latest | Numerical computing |
| **requests** | Latest | HTTP client for API |
| **pyyaml** | Latest | Config file parsing |

### Key Files

| File | LOC | Responsibility |
|------|-----|-----------------|
| `app.py` | ~200 | Main Dash app entry, registration |
| `login_app.py` | 844 | Separate login server (:8050) |
| `layout.py` | 2,095 | Dashboard structure (tabs, grids) |
| `callbacks.py` | 2,323 | Interactive state management |
| `components_map.py` | 1,662 | Leaflet map integration |
| `Model_1_realtime_simulation.py` | 2,206 | ML anomaly detection engine |
| `engine_fallback.py` | ~150 | Demo mode (no ML) |
| `data.py` | ~200 | Excel/CSV loading, caching |
| `processing.py` | ~150 | Data cleaning, aggregations |
| `false_alarm_patterns.py` | ~180 | Pattern matching & learning |
| `utils.py` | ~120 | Formatting, calculations |

### Dashboard Structure

**Ports:**
- Dashboard: `:8051`
- Login Portal: `:8050`

**Tabs:**
1. **Overview** - KPIs, incident summary, time-series charts
2. **Events** - Incident cards with action buttons (Acknowledge, Watch, Escalate, Resolve, Ignore)
3. **Log** - Audit trail of all actions taken
4. **GIS Map** - Interactive NSW map with school markers

**Features:**
- Deep Ocean theme (navy/cyan gradients, glassmorphism)
- Real-time data refresh
- Export to CSV
- Role-based UI elements (buttons/fields)

### ML Engine (Model_1_realtime_simulation.py)

**Multi-Signal Weighting:**
```python
confidence = (
    0.4 * mnf_score +        # Minimum Night Flow anomaly
    0.2 * residual_score +   # Consumption residual
    0.2 * cusum_score +      # Cumulative sum control
    0.1 * afterhours_score + # After-hours usage
    0.1 * burst_score        # Burst detection
)
```

**Output:** 0-100% confidence score

**Baseline:** 28-day rolling window (15 days normal, 15 days anomaly)

---

## Authentication Flow

```
User
  │
  ├─→ POST /auth/login (email, password)
  │   └─→ Backend validates, generates JWT
  │       ├─ Access Token (30 min, HS256)
  │       └─ Refresh Token (7 days, HS256)
  │
  ├─→ GET /incidents/ + Bearer {access_token}
  │   └─→ Backend verifies token, returns data
  │
  └─→ POST /auth/refresh (refresh_token)
      └─→ Backend issues new access token
```

**Default Users (auto-created):**
- Username: `admin` | Password: `admin123` | Role: `admin`
- Username: `operator` | Password: `operator123` | Role: `operator`

---

## Data Flow

```
1. Water Meter Data (Excel/CSV)
   ↓
2. frontend/data.py (load + validate)
   ↓
3. frontend/processing.py (normalize, aggregate)
   ↓
4. frontend/Model_1_realtime_simulation.py (scoring)
   ↓
5. Confidence score (0-100%) → backend/incidents
   ↓
6. Dashboard visualization + alerts
   ↓
7. User action (Acknowledge/Resolve) → backend
```

---

## Directory Size Estimation

| Directory | Approx LOC | Files |
|-----------|-----------|-------|
| backend/app | 903 | 14 |
| frontend (core) | 12,207 | 13 |
| .claude | variable | 20+ |
| docs | 3,500+ | 6+ |
| **Total** | **~15,500** | **50+** |

---

## Key Configuration Files

### Backend
- **`.env`** - Environment variables (SECRET_KEY, DATABASE_URL, DEBUG)
- **`app/core/config.py`** - Pydantic settings class

### Frontend
- **`config_leak_detection.yml`** - Data source path (demo vs. production)
- **`assets/*.css`** - Styling (login-styles.css, _design-system.css)

### Project
- **`.repomixignore`** - Files to exclude from codebase scan
- **`CLAUDE.md`** - AI development guidelines
- **`.env.example`** - Template for .env

---

## Development Workflow

### Setup
```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && pip install -r requirements.txt
python app.py  # Starts dashboard on :8051
python login_app.py  # Starts login portal on :8050 (separate terminal)
```

### Testing
```bash
cd backend && pytest
cd frontend && python test_pattern_matching.py
```

### Database Reset
```bash
cd backend && del leak_detection.db
# Restart backend to recreate with default users
```

---

## Known Limitations

1. **SQLite scalability** - Single-file database, not ideal for >100k records
2. **No clustering** - Single-server deployment only
3. **Synchronous ML engine** - Blocks during scoring on large datasets
4. **Mock GIS data** - Uses static JSON, not live map tiles
5. **No email/SMS** - Alerts manual only

---

## Performance Metrics

| Metric | Typical | Benchmark |
|--------|---------|-----------|
| API response (GET) | ~50ms | <200ms target |
| Dashboard load | ~1.2s | <2s target |
| ML scoring | ~100ms per property | <1s per 10 properties |
| Database query | ~30ms | <50ms target |
| Concurrent sessions | 50+ | Tested |

---

## Version History

- **v2.1.2** (Jan 2026) - Fix duplicate incident cards
- **v2.1.0** (Dec 2025) - WaterWatch Edition, Deep Ocean theme
- **v2.0.0** (Dec 2025) - Complete Edition (Dashboard + Backend)
- **v1.0.0** (Initial) - Dashboard prototype

---

## Related Files

- [Code Standards](./code-standards.md) - Conventions & patterns
- [System Architecture](./system-architecture.md) - Design decisions
- [Deployment Guide](./deployment-guide.md) - Setup instructions
