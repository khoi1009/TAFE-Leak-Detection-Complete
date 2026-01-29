# WaterWatch Documentation

**Project:** TAFE Leak Detection System | **Version:** 2.1.2 | **Last Updated:** January 29, 2026

Welcome to the WaterWatch documentation hub. This directory contains comprehensive guides for developers, operators, and stakeholders.

---

## Quick Navigation

### For New Developers

Start here to understand the project:

1. **[Project Overview](./project-overview-pdr.md)** - Business goals, requirements, stakeholders
   - Problem statement & solution overview
   - Functional & non-functional requirements
   - Success metrics & acceptance criteria

2. **[Codebase Summary](./codebase-summary.md)** - Project structure & components
   - Directory organization
   - Key files & their purposes
   - Dependencies & versions
   - Database schema

3. **[System Architecture](./system-architecture.md)** - Technical design & data flow
   - Component interaction diagrams
   - API endpoints reference
   - Authentication & RBAC system
   - Data flow architecture

4. **[Code Standards](./code-standards.md)** - Development conventions & patterns
   - Naming conventions
   - Code organization
   - Function & method standards
   - Backend & frontend patterns

### For Operations & DevOps

Ready to deploy? Follow these guides:

1. **[Deployment Guide](./deployment-guide.md)** - Setup, configuration, operations
   - Prerequisites & installation
   - Running the system (all options)
   - Environment configuration
   - Troubleshooting & maintenance
   - Production deployment

2. **[Project Roadmap](./project-roadmap.md)** - Future features & timeline
   - Current release status (v2.1.2)
   - Planned features (v2.2 - v3.0)
   - Timeline & resource estimates
   - Risk register

---

## Documentation Files

| File | Lines | Purpose | Audience |
|------|-------|---------|----------|
| **README.md** | This file | Navigation & index | Everyone |
| **project-overview-pdr.md** | 298 | Business requirements & PDR | PMs, Stakeholders |
| **codebase-summary.md** | 382 | Project structure & components | Developers, Leads |
| **system-architecture.md** | 627 | Technical design & data flow | Architects, Senior Devs |
| **code-standards.md** | 787 | Development conventions | All Developers |
| **deployment-guide.md** | 757 | Setup & operations | DevOps, Operators |
| **project-roadmap.md** | 480 | Future planning & timeline | PMs, Leads |
| **TOTAL** | 3,331 | Comprehensive coverage | All roles |

---

## Common Workflows

### I want to...

#### ...understand the project
→ Read [Project Overview](./project-overview-pdr.md) (5 min)

#### ...set up the development environment
→ Follow [Deployment Guide - Installation](./deployment-guide.md#installation) (10 min)

#### ...add a new API endpoint
→ Check [System Architecture - API Pattern](./system-architecture.md#backend-architecture) + [Code Standards - Backend Patterns](./code-standards.md#backend-patterns) (15 min)

#### ...create a new dashboard component
→ Check [Code Standards - Frontend Patterns](./code-standards.md#frontend-patterns) + [Codebase Summary - Frontend](./codebase-summary.md#frontend-architecture) (15 min)

#### ...deploy to production
→ Follow [Deployment Guide - Production](./deployment-guide.md#production-deployment) (30 min)

#### ...understand the ML scoring
→ Read [System Architecture - ML Engine](./system-architecture.md#ml-engine-model_1_realtime_simulationpy) (10 min)

#### ...troubleshoot a problem
→ See [Deployment Guide - Troubleshooting](./deployment-guide.md#troubleshooting) (5 min)

#### ...plan the next release
→ Review [Project Roadmap](./project-roadmap.md) (20 min)

---

## Technology Stack Reference

### Backend
- **Framework:** FastAPI 0.109+
- **Database:** SQLite + aiosqlite (async)
- **Auth:** JWT (HS256), bcrypt passwords
- **ORM:** SQLAlchemy 2.0 async
- **Server:** Uvicorn

### Frontend
- **Framework:** Dash (Plotly)
- **Visualization:** Plotly, Leaflet maps
- **Theme:** UI UX Pro Max + Deep Ocean
- **Auth Portal:** Dash + Deep Ocean theme
- **Landing Page:** Next.js 13 (optional)

### Key Dependencies
- Python 3.9+
- FastAPI, Uvicorn, SQLAlchemy 2.0, aiosqlite
- Dash, Plotly, Pandas, NumPy
- Pydantic 2.0, python-jose, passlib/bcrypt

---

## Key Concepts

### Authentication Flow
```
Login → JWT tokens (access 30min, refresh 7d) → Protected endpoints
Refresh → New access token → Continue session
```

### Incident Lifecycle
```
open → acknowledged → watching → escalated → resolved
   └──────────────────────────────────────────↓
                                          ignored (false alarm)
```

### ML Scoring
```
Multi-signal weighting (MNF, RESIDUAL, CUSUM, AFTERHRS, BURSTBF)
→ 0-100% confidence score
→ Pattern matching (learn false alarms)
→ Alert if >70% (configurable)
```

### Role-Based Access
- **Admin:** Full system access, user management
- **Manager:** Team assignment, incident management
- **Operator:** Assigned incidents only
- **Viewer:** Read-only access

---

## API Quick Reference

**Base URL:** `http://localhost:8000/api/v1`

### Auth
- `POST /auth/login` - Get tokens
- `POST /auth/refresh` - Extend session
- `GET /auth/me` - Current user

### Incidents
- `GET /incidents/` - List with filtering/pagination
- `POST /incidents/` - Create incident
- `PATCH /incidents/{id}` - Update status/assignment
- `GET /incidents/stats` - Summary statistics

### Schools
- `GET /schools/` - List all schools
- `GET /schools/search?q=name` - Search
- `GET /schools/alerts` - Schools with alerts

**API Docs:** http://localhost:8000/docs (Swagger UI)

---

## Access Points (Development)

| Service | URL | Purpose |
|---------|-----|---------|
| Landing Page | http://localhost:3000 | Marketing (optional) |
| Login Portal | http://127.0.0.1:8050 | Authentication |
| Dashboard | http://127.0.0.1:8051 | Main UI |
| API | http://127.0.0.1:8000 | REST endpoints |
| API Docs | http://127.0.0.1:8000/docs | Swagger UI |

### Default Credentials
- Username: `admin` | Password: `admin123` | Role: Admin
- Username: `operator` | Password: `operator123` | Role: Operator

---

## Database Schema Quick Reference

### Users Table
```sql
id, email, username, hashed_password, full_name, role, is_active,
created_at, updated_at, last_login
```

### Incidents Table
```sql
id, property_id, school_name, confidence, signals (JSON),
status, assigned_to, cost_estimate, notes, created_at, updated_at
```

Full schema: See [System Architecture - Database Schema](./system-architecture.md#database-schema)

---

## File Organization Best Practices

### Python Naming
- **Files:** `kebab-case-descriptive.py` (self-documenting)
- **Classes:** `PascalCase`
- **Functions:** `snake_case`
- **Constants:** `UPPER_SNAKE_CASE`

### File Size Guidelines
- Python files: <200 LOC
- API endpoints: <150 LOC
- Components: <100 LOC

See [Code Standards - Organization](./code-standards.md#code-organization)

---

## Common Issues & Solutions

| Problem | Solution |
|---------|----------|
| "Address already in use" | Kill process on port: `lsof -i :8000` |
| "Connection refused" | Check CORS config, restart backend |
| "Database locked" | Restart to release lock, or use PostgreSQL |
| "Token expired" | Call `/auth/refresh` endpoint |
| Import errors | Install dependencies: `pip install -r requirements.txt` |

Full troubleshooting: [Deployment Guide - Troubleshooting](./deployment-guide.md#troubleshooting)

---

## Development Workflow

### Setup (First Time)
```bash
# Clone repo
git clone https://github.com/khoi1009/TAFE-Leak-Detection-Complete.git
cd TAFE-Leak-Detection-Complete

# Copy & configure .env
cp .env.example .env

# Install dependencies
cd backend && pip install -r requirements.txt
cd ../frontend && pip install -r requirements.txt

# Run all services
cd .. && ./start_all.bat  # Windows
# or bash start_all.bat  # Linux/macOS
```

### Daily Development
1. Pull latest changes: `git pull`
2. Create feature branch: `git checkout -b feature/my-feature`
3. Make changes, test locally
4. Commit with conventional format: `git commit -m "feat(scope): description"`
5. Push and create PR
6. Request review

### Testing
```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && python test_pattern_matching.py
```

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| API response | <200ms | GET typical |
| Dashboard load | <2s | Initial, includes data |
| ML scoring | <1s | Per 10 properties |
| Database query | <50ms | Indexed queries |
| Concurrent users | 50+ | Dashboard sessions |

Current performance: See [System Architecture - Performance](./system-architecture.md#performance-optimization)

---

## Security Checklist

- [ ] SECRET_KEY changed from default
- [ ] DEBUG=false in production
- [ ] HTTPS enabled
- [ ] CORS origins restricted
- [ ] Default credentials changed
- [ ] Database backups in place
- [ ] Logs monitored for errors
- [ ] API rate limiting enabled (v2.2+)

See [Deployment Guide - Security](./deployment-guide.md#security-hardening)

---

## Support & Resources

### Getting Help

1. **Check the docs** - Most answers are in these files
2. **Review GitHub issues** - Search existing problems
3. **Check API docs** - http://localhost:8000/docs
4. **Run health check** - `curl http://127.0.0.1:8000/health`

### Documentation Maintenance

**If you find outdated information:**
1. Note the file and section
2. Check current code
3. Create issue or PR with updates
4. Assign to documentation owner

**Last documentation audit:** January 29, 2026

---

## Contribution Guidelines

### Before Contributing
1. Read [Code Standards](./code-standards.md)
2. Check [Project Roadmap](./project-roadmap.md) for planned features
3. Review existing code for patterns

### Making Changes
1. Follow naming conventions
2. Keep files <200 LOC
3. Add docstrings
4. Test before committing
5. Use conventional commits
6. Update relevant documentation

### Submitting PR
1. Link to related issue/feature
2. Describe changes clearly
3. Include test results
4. Request review from lead

---

## Version History

| Version | Date | Status | Highlights |
|---------|------|--------|-----------|
| **2.1.2** | Jan 2026 | Current | Duplicate fix, dev notes |
| **2.1.1** | Jan 2026 | Stable | Demo launcher added |
| **2.1.0** | Dec 2025 | Stable | WaterWatch Edition, Deep Ocean |
| **2.0.0** | Dec 2025 | Stable | Complete Edition (Dashboard+API) |
| **1.0.0** | Past | EOL | Initial prototype |

Future: **v2.2** (Q2 2026), **v2.3** (Q3 2026), **v3.0** (Q4 2026)

See [Project Roadmap](./project-roadmap.md) for details

---

## Contact & Escalation

### Support Levels

- **P1 (System Down):** 1-hour response, 4-hour resolution
- **P2 (Major Feature Down):** 2-hour response, 8-hour resolution
- **P3 (Minor Issues):** 24-hour response, 5-day resolution

### Contacts

- **Technical:** admin@tafe.nsw.edu.au
- **Research:** research@griffith.edu.au
- **Operations:** facilities@tafe.nsw.edu.au

---

## Document Metadata

- **Total Documentation:** 3,331 lines across 6 files
- **Coverage:** Backend, frontend, architecture, operations, roadmap
- **Last Updated:** January 29, 2026
- **Next Audit:** April 2026 (before v2.2 release)
- **Maintained By:** Documentation Team

---

## Related Resources

- **GitHub Repository:** https://github.com/khoi1009/TAFE-Leak-Detection-Complete
- **Main README:** ../README.md
- **Issue Tracker:** GitHub Issues
- **Project Board:** GitHub Projects
- **API Playground:** http://localhost:8000/docs

---

**Happy coding! For questions or suggestions, open an issue on GitHub or contact the documentation team.**
