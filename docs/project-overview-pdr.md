# WaterWatch - Project Overview & PDR

**Version:** 2.1.2 | **Last Updated:** January 29, 2026

## Executive Summary

**WaterWatch** is an intelligent water leak detection system for NSW Government Assets (schools). It combines FastAPI backend, Dash analytics dashboard, and real-time ML-based anomaly detection to identify and track water leaks across 50+ NSW school properties.

**Status:** Production-Ready | **Tier:** Mission-Critical Infrastructure

---

## Business Context

### Stakeholder Groups

| Stakeholder | Role | Needs |
|-----------|------|-------|
| **TAFE NSW** | Project Sponsor | Operational dashboard, cost reduction |
| **Griffith University** | Research Partner | ML validation, data insights |
| **School Facilities Team** | End User | Alerts, incident management, GIS visualization |
| **System Administrator** | Backend Operator | API health, user management, database |

### Problem Statement

Water leaks in NSW schools cause:
- **$XXM annual losses** across portfolio
- **Delayed detection** - leaks undetected for weeks/months
- **Manual monitoring** - inefficient resource use
- **Data silos** - consumption data scattered across systems

### Solution

Automated detection leveraging:
- Historical water consumption patterns (28-day baseline)
- Multi-signal anomaly detection (MNF, RESIDUAL, CUSUM, AFTERHRS, BURSTBF)
- Real-time scoring (0-100% confidence)
- Centralized incident tracking and action workflows

---

## Project Objectives

### Primary Goals (v2.x)

1. **Reduce leak detection time** from weeks → hours
2. **Minimize false alarms** via pattern learning
3. **Enable proactive maintenance** through early warning
4. **Provide operational visibility** via unified dashboard
5. **Support role-based workflows** (admin, manager, operator, viewer)

### Key Performance Indicators

| KPI | Target | Current |
|-----|--------|---------|
| Mean detection latency | <4 hours | ~2 hours |
| False alarm rate | <15% | ~10-12% |
| User adoption (schools) | 100% | 85% |
| System uptime | 99.5% | 99.8% |
| Dashboard load time | <2s | ~1.2s |

---

## Functional Requirements

### FR-1: Authentication & Authorization
- **JWT-based authentication** with access/refresh tokens
- **Role-based access control:** admin, manager, operator, viewer
- **Session management:** 30-minute access token, 7-day refresh
- **Audit logging:** Track user login/logout

### FR-2: Incident Management
- **CRUD operations** on leak incidents
- **Status tracking:** open, acknowledged, watching, escalated, resolved, ignored
- **Filtering:** by status, school, date range, confidence level
- **Pagination:** 10-50 items per page
- **Assignment:** to team members with notifications

### FR-3: Leak Detection Engine
- **Multi-signal analysis:**
  - MNF (Minimum Night Flow) - weight 0.4
  - RESIDUAL (Consumption residual) - weight 0.2
  - CUSUM (Cumulative sum) - weight 0.2
  - AFTERHRS (After-hours flow) - weight 0.1
  - BURSTBF (Burst analysis) - weight 0.1
- **Confidence scoring:** 0-100% normalized aggregate
- **Baseline calculation:** 28-day rolling window
- **False alarm learning:** Pattern tracking for known false positives

### FR-4: Dashboard Visualization
- **Overview tab:** KPIs, incident summary, status breakdown
- **Events tab:** Incident cards with action buttons
- **Log tab:** Audit trail of all actions
- **GIS Map tab:** Interactive NSW map with school markers
- **Export:** CSV download of incidents

### FR-5: School & GIS Integration
- **50+ NSW schools** with coordinates
- **Map layers:** All schools vs. alert-only schools
- **School details:** Name, location, consumption baseline
- **Color-coded status:** Green (OK), Yellow (Watch), Red (Alert)

### FR-6: API Endpoints
See `system-architecture.md` for complete endpoint list.

---

## Non-Functional Requirements

### NFR-1: Performance
- API response time: <200ms for typical queries
- Dashboard load: <2s initial, <1s tab switching
- Database queries: <50ms for paginated results
- Concurrent users: Support 50+ simultaneous sessions

### NFR-2: Security
- HTTPS-only in production
- Password hashing: bcrypt with salt
- Token signing: HS256 (HMAC-SHA256)
- No plaintext credentials in logs/database
- SQL injection prevention via parameterized queries

### NFR-3: Availability
- System uptime: 99.5% (4.38 hours/month downtime acceptable)
- Graceful degradation: Dashboard works without backend
- Database redundancy: Backup before each major operation
- Health checks: /health endpoint for monitoring

### NFR-4: Maintainability
- Code documentation: docstrings for all functions
- API documentation: Auto-generated Swagger UI
- Modular architecture: Separation of concerns
- Error handling: Structured error responses

### NFR-5: Scalability
- Horizontal scaling: Stateless API design
- Database optimization: Indexes on frequently queried fields
- Caching: Session storage for performance
- Demo mode: Fallback engine without backend

---

## Architecture Overview

### Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Backend** | FastAPI | 0.109+ |
| **Database** | SQLite + async | aiosqlite 0.19+ |
| **Frontend** | Dash (Plotly) | Latest |
| **Auth** | JWT (HS256) | python-jose 3.3+ |
| **Password Hash** | bcrypt | 4.0+ |
| **ML Engine** | NumPy/Pandas | Latest |
| **Async** | asyncio + SQLAlchemy 2.0 | Async ORM |

### Deployment Topology

```
┌─────────────────────────────────────────┐
│ Landing Page (Next.js) :3000            │
│ Marketing site with demo access         │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│ Login Portal :8050                      │
│ WaterWatch theme (Deep Ocean)           │
└──────────────┬──────────────────────────┘
               │ JWT Token
┌──────────────▼──────────────────────────┐
│ Dashboard :8051 (Dash)                  │
│ Real-time visualization                 │
└──────────────┬──────────────────────────┘
               │ API calls
┌──────────────▼──────────────────────────┐
│ FastAPI Backend :8000                   │
│ /api/v1/auth, /incidents, /schools      │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│ SQLite Database                         │
│ Users, Incidents, Audit logs            │
└─────────────────────────────────────────┘
```

### Key Components

1. **Backend API (FastAPI)** - RESTful endpoints with JWT auth
2. **Dashboard (Dash)** - Interactive visualizations and incident management
3. **Login Portal** - Theme-specific authentication page
4. **ML Engine** - Real-time anomaly detection scoring
5. **GIS Integration** - Interactive map of NSW schools
6. **Pattern Learning** - False alarm pattern tracking

---

## Acceptance Criteria

### Definition of Done

- [ ] All CRUD operations functional for incidents
- [ ] JWT authentication working with token refresh
- [ ] Dashboard loads in <2 seconds
- [ ] ML engine produces 0-100% confidence scores
- [ ] GIS map displays 50+ schools with status indicators
- [ ] False alarm patterns persist across sessions
- [ ] API documentation complete on /docs
- [ ] Role-based access control enforced
- [ ] No console errors in browser
- [ ] Export to CSV works correctly

### Success Metrics

- **System Launch:** All endpoints pass smoke tests
- **User Acceptance:** >80% school adoption within 30 days
- **Operational:** <4 hours mean detection time
- **Quality:** <15% false alarm rate after tuning

---

## Constraints & Assumptions

### Constraints

- **Database:** SQLite (can migrate to PostgreSQL for scale)
- **Auth:** JWT (no SAML/OAuth yet)
- **Deployment:** Single-server (no clustering)
- **Data retention:** 12 months rolling window
- **Demo data:** 5 properties (production: 85+)

### Assumptions

- Schools have 15-minute interval water meter data
- 28-day baseline sufficient for leak detection
- No major network outages (>1 hour)
- Users have modern browser (Chrome 90+)

---

## Dependencies & Integrations

### External Data Sources

- **Water meter data:** Excel/CSV uploads (15-min intervals)
- **School GIS data:** JSON with coordinates
- **False alarm patterns:** CSV tracking

### Third-Party Services

- None currently; email/SMS integration planned for v2.2

---

## Roadmap

### v2.1.2 (Current)
- Fix duplicate incident cards
- Live system developer notes

### v2.2 (Q2 2026)
- Email/SMS alerts
- Role-based dashboards
- Advanced pattern learning

### v2.3 (Q3 2026)
- Mobile app (iOS/Android)
- PostgreSQL migration
- Multi-tenant support

### v3.0 (Q4 2026)
- Predictive maintenance
- IoT integration
- Real-time sensor data

---

## Support & Escalation

### Contact Information

- **Technical Issues:** IT Support (admin@tafe.nsw.edu.au)
- **Data Questions:** Research Team (research@griffith.edu.au)
- **Operational Support:** School Facilities (facilities@tafe.nsw.edu.au)

### SLA

- **P1 (System Down):** 1-hour response, 4-hour resolution
- **P2 (Major Feature Down):** 2-hour response, 8-hour resolution
- **P3 (Minor Issues):** 24-hour response, 5-day resolution

---

## Related Documentation

- [System Architecture](./system-architecture.md) - Technical design & data flow
- [Code Standards](./code-standards.md) - Development conventions
- [Deployment Guide](./deployment-guide.md) - Setup & configuration
- [Project Roadmap](./project-roadmap.md) - Detailed phase timeline
