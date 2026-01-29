# Project Roadmap

**Version:** 2.1.2 | **Updated:** January 29, 2026 | **Status:** Active Development

---

## Release Overview

```
v1.0 (Past)      v2.0 (Dec 2025)     v2.1 (Current)      v2.2 (Q2 2026)      v3.0 (Q4 2026)
│                │                    │                   │                   │
Prototype ─────→ Complete Edition ──→ WaterWatch Edition ─→ Advanced Features ─→ Enterprise
                 (Dashboard+API)      (Deep Ocean Theme)   (Alerts, Mobile)    (Predictive, IoT)
```

---

## Current Release: v2.1.2 (January 2026)

**Status:** Production-Ready ✅ | **Release Date:** January 29, 2026

### Features Completed

- [x] FastAPI backend with JWT authentication
- [x] Dash dashboard with 4 interactive tabs
- [x] GIS map integration with 50 NSW schools
- [x] Real-time ML anomaly detection engine
- [x] False alarm pattern learning
- [x] Role-based access control (admin, manager, operator, viewer)
- [x] Deep Ocean themed login portal
- [x] Demo mode (no backend required)
- [x] Next.js landing page (optional)

### Recent Updates (v2.1.x)

#### v2.1.2 (January 29, 2026)
- Fix duplicate incident cards deduplication by site_id + start_day
- Add live system developer notes in README
- Document water usage pattern chart considerations

#### v2.1.1 (January 20, 2026)
- Add WaterWatch demo launcher
- Live system developer notes

#### v2.1.0 (December 8, 2025)
- Rebrand to WaterWatch
- Deep Ocean Data login theme
- Hydro-Pulse loading animations
- Landing page support
- Separated CSS for login vs dashboard

### Known Issues (v2.1.x)

| Issue | Severity | Workaround | Status |
|-------|----------|-----------|--------|
| SQLite concurrency | Medium | Use single-threaded mode | Planned for v2.3 |
| Dashboard memory usage | Low | Reduce update frequency | Monitor |
| ML scoring latency | Low | Cache scores for 30 sec | Implemented v2.1 |

### Support Status

- **Bug Fixes:** Active (weekly)
- **Security Patches:** Active (as needed)
- **New Features:** Minimal (focus on v2.2)
- **End of Life:** December 2026

---

## Next Release: v2.2 (Q2 2026)

**Status:** Planning | **Target Date:** April-June 2026 | **Priority:** HIGH

### Feature Roadmap

#### 1. Email & SMS Alerts (Core Priority)

**Description:** Notify facilities team of critical leaks immediately

**Requirements:**
- Integration with email service (SMTP or SendGrid)
- SMS via Twilio or AWS SNS
- Alert templates (incident, escalation, resolution)
- Quiet hours configuration (9 PM - 7 AM)
- Delivery retry logic

**Files to Create/Modify:**
- `backend/app/services/notification_service.py` (NEW)
- `backend/app/api/alerts.py` (NEW)
- `backend/requirements.txt` (add sendgrid, twilio)
- `backend/app/models/notification_log.py` (NEW)

**API Endpoints:**
```
POST /api/v1/alerts/subscribe
PATCH /api/v1/alerts/settings
GET /api/v1/alerts/delivery-log
```

**Success Criteria:**
- Email delivered within 1 minute of incident
- SMS delivered within 30 seconds
- 99% delivery rate
- Audit trail of all notifications

#### 2. Role-Specific Dashboards

**Description:** Customize dashboard based on user role

**Requirements:**
- Admin: Full access, all metrics
- Manager: Team assignment, incident management
- Operator: Assigned incidents only
- Viewer: Read-only, no actions

**Files to Modify:**
- `frontend/layout.py` (role-aware tabs)
- `frontend/components.py` (conditional rendering)
- `frontend/callbacks.py` (role-based filtering)

**Features:**
- Admin: User management, system settings, advanced reports
- Manager: Team workload, bulk assignment, approval workflows
- Operator: My incidents, action log, quick actions
- Viewer: Statistics, maps, no action buttons

**Success Criteria:**
- Operators see only assigned incidents
- Admins can view all
- No unauthorized API access (verified server-side)

#### 3. Advanced Pattern Learning

**Description:** Improve false alarm detection with ML

**Requirements:**
- Learn from resolved/ignored incidents
- Seasonal pattern recognition
- Time-of-day patterns (weekday morning, weekend, etc.)
- School-specific baselines

**Files to Modify:**
- `frontend/false_alarm_patterns.py` (expand logic)
- `frontend/Model_1_realtime_simulation.py` (integrate patterns)

**Algorithm:**
```python
# Extract pattern features
pattern = {
    "school_id": incident.school_id,
    "day_of_week": incident.day_of_week,
    "time_of_day": incident.time_of_day,  # morning, afternoon, evening
    "season": get_season(incident.date),
    "consumption_profile": incident.consumption_baseline_match
}

# Store in database (not CSV)
db.learned_patterns.insert(pattern)

# On next detection:
if is_similar_pattern(new_incident, learned_patterns):
    confidence -= 25  # Reduce confidence
```

**Success Criteria:**
- False alarm rate drops from 12% to <8%
- Precision improves to >85%

#### 4. Advanced Reporting & Export

**Description:** Generate reports for stakeholders

**Requirements:**
- Monthly incident summary (by school, by status)
- Water savings estimate (if leak fixed)
- Trend analysis (incidents over time)
- Export formats: PDF, Excel, CSV

**Files to Create:**
- `backend/app/services/report_generator.py` (NEW)
- `backend/app/api/reports.py` (NEW)

**API Endpoints:**
```
GET /api/v1/reports/monthly
GET /api/v1/reports/school/{id}
GET /api/v1/reports/trends
POST /api/v1/reports/export
```

**Report Contents:**
- Incidents by status
- Average detection time
- Schools most affected
- Cost savings summary
- Forecast for next month

**Success Criteria:**
- PDF generated in <5 seconds
- All data accurate
- Customizable date ranges

#### 5. Incident Assignment & Workflows

**Description:** Workflow for incident triage and assignment

**Requirements:**
- Assign to specific team members
- Escalation path (operator → manager → director)
- SLA tracking (target resolution time)
- Notes & comments on incidents

**Files to Modify:**
- `backend/app/models/incident.py` (add assigned_to, sla_deadline)
- `backend/app/api/incidents.py` (add assignment endpoint)
- `frontend/layout.py` (show assignment UI)

**Workflow States:**
```
open → acknowledged → watching → escalated → resolved
   ↓
  ignored (false alarm)
```

**Success Criteria:**
- Assignment visible to all team members
- SLA tracked automatically
- Escalation triggers notifications

### Timeline: v2.2 Phases

| Phase | Duration | Focus |
|-------|----------|-------|
| **1. Setup** | 1 week | Environment, architecture, task breakdown |
| **2. Email/SMS** | 3 weeks | Notification service, templates, testing |
| **3. Role Dashboards** | 2 weeks | UI components, backend filtering |
| **4. Pattern Learning** | 2 weeks | Algorithm, database, integration |
| **5. Reporting** | 2 weeks | Report generation, exports, testing |
| **6. Workflows** | 1 week | Assignment, SLA tracking, UI |
| **7. Testing & QA** | 1 week | Full regression, performance, security |
| **8. Release** | 1 week | Documentation, deployment prep |

**Total Effort:** ~13 weeks | **Team Size:** 2-3 developers | **Target:** April-June 2026

---

## Future Releases: v2.3 - v3.0 (Q3-Q4 2026)

### v2.3 (Q3 2026) - Enterprise Ready

**Focus:** Scalability, Multi-tenancy, Mobile

**Features:**
- [ ] Mobile app (iOS/Android React Native)
- [ ] PostgreSQL migration from SQLite
- [ ] Multi-tenant architecture (support multiple districts)
- [ ] Advanced caching (Redis)
- [ ] Horizontal scaling (load balancer + multiple API instances)
- [ ] API rate limiting & quotas
- [ ] Webhook integration for third-party systems

**Estimated Effort:** 16 weeks | **Team:** 3-4 developers

#### Migration Plan (SQLite → PostgreSQL)

```sql
-- New PostgreSQL schema
CREATE TABLE incidents_v2 (
  id BIGSERIAL PRIMARY KEY,
  tenant_id INTEGER NOT NULL,
  property_id VARCHAR(100) NOT NULL,
  school_name VARCHAR(255) NOT NULL,
  confidence FLOAT NOT NULL,
  signals JSONB NOT NULL,
  status VARCHAR(20) DEFAULT 'open',
  assigned_to INTEGER,
  sla_deadline TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  FOREIGN KEY (assigned_to) REFERENCES users(id),
  INDEX idx_tenant_status (tenant_id, status),
  INDEX idx_school_name (school_name)
);

-- Migration script
INSERT INTO incidents_v2 SELECT * FROM incidents;
```

#### Mobile App Features

- Native iOS (Swift) & Android (Kotlin) apps
- Offline support (sync when online)
- Push notifications
- Camera integration (upload photos of damage)
- Signature capture for technician sign-off

### v3.0 (Q4 2026) - Predictive & IoT

**Focus:** Predictive maintenance, Real-time IoT integration

**Features:**
- [ ] Predictive leak forecast (next 7-14 days)
- [ ] IoT sensor integration (real-time meter data)
- [ ] Automated response (valve shutoff for critical leaks)
- [ ] AI-powered root cause analysis
- [ ] Integration with SCADA systems
- [ ] Climate/weather correlation
- [ ] Benchmarking vs. similar schools

**ML Enhancements:**
- Time series forecasting (LSTM/Prophet)
- Anomaly detection refinement
- Causal analysis (what causes this school's leaks?)

**Estimated Effort:** 20 weeks | **Team:** 4-5 developers + ML engineer

---

## Dependency & Constraint Analysis

### External Dependencies

| Dependency | Status | Risk | Mitigation |
|-----------|--------|------|-----------|
| SQLite | ✅ Stable | Low | Migrate to PostgreSQL in v2.3 |
| FastAPI | ✅ Stable | Low | Monitor security patches |
| Dash/Plotly | ✅ Stable | Low | Version pinning in requirements |
| Python 3.9+ | ✅ Stable | Low | Support 3.9-3.11 |
| Email/SMS services | ⚠️ Third-party | Medium | Use multiple providers, fallback |

### Resource Constraints

| Resource | Available | Needed (v2.2) | Gap |
|----------|-----------|---------------|-----|
| Developer time | TBD | 13 weeks | TBD |
| Testing environment | ✅ Available | ✅ Yes | 0 |
| Production hardware | ⚠️ Shared | ⚠️ Maybe | TBD |
| Budget | TBD | TBD | TBD |

---

## Success Metrics

### Current (v2.1.2)

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| System uptime | 99.5% | 99.8% | ✅ Exceeds |
| API response time | <200ms | ~50-100ms | ✅ Exceeds |
| Dashboard load | <2s | ~1.2s | ✅ Exceeds |
| False alarm rate | <15% | ~10-12% | ✅ Exceeds |
| School adoption | 100% | 85% | ⚠️ In progress |

### v2.2 Goals

| Metric | Target | Improvement |
|--------|--------|------------|
| Mean detection time | <3 hours | From 4 hours |
| False alarm rate | <8% | From 10-12% |
| User satisfaction | >4.0/5.0 | New measure |
| Email delivery | >99% | New measure |
| Mobile app downloads | 500+ | New measure |

### v3.0 Goals

| Metric | Target |
|--------|--------|
| Predictive accuracy | >75% (7-day forecast) |
| Cost savings per school | $5,000-10,000/year |
| System users | 200+ (across districts) |
| API usage | 1M+ requests/month |

---

## Risk Register

### High Risk

| Risk | Impact | Probability | Mitigation |
|------|--------|------------|-----------|
| PostgreSQL migration breaks existing APIs | Critical | Medium | Comprehensive testing, blue-green deployment |
| Email service provider outage | High | Low | Multi-provider fallback, local queue |
| Data breach (incident data) | Critical | Low | Encryption at rest, HTTPS, audit logging |

### Medium Risk

| Risk | Impact | Probability | Mitigation |
|------|--------|------------|-----------|
| Performance degradation with 10k+ incidents | High | Medium | Database optimization, archival strategy |
| Team turnover delays release | High | Low | Documentation, knowledge sharing |
| New Python version incompatibility | Medium | Low | Continuous testing, early upgrades |

### Low Risk

| Risk | Impact | Probability | Mitigation |
|------|--------|------------|-----------|
| CSS framework updates break styling | Low | Low | Regular dependency updates, testing |
| Third-party library deprecation | Low | Medium | Monitor GitHub releases, plan migrations |

---

## Budget & Resource Planning

### v2.2 Estimate

| Resource | Cost | Notes |
|----------|------|-------|
| Developer time (3 FTE) | $120k | 13 weeks @ standard rate |
| Testing environment | $2k | Virtual machines, cloud services |
| Third-party services | $5k | Email/SMS delivery costs |
| Tools & licenses | $1k | APM, monitoring, testing tools |
| **Total** | **$128k** | |

### ROI Calculation

**Benefits (Annual):**
- Leak detection savings: $500k (5 schools × $100k/year)
- Staff efficiency: $50k (faster incident response)
- **Total annual benefit:** $550k

**Payback period:** 3 months (if deployed to 5 schools)

---

## Deployment Strategy

### Phased Rollout

**Phase 1: Pilot (3 months)**
- Deploy to 5 schools
- Gather feedback
- Fine-tune ML models

**Phase 2: Early Adopters (6 months)**
- Deploy to 15 schools
- Train facilities teams
- Document best practices

**Phase 3: Full Rollout (12 months)**
- Deploy to all 50+ schools
- Integrate with existing systems
- Ongoing support

### Rollback Plan

If critical issues discovered:
1. Revert to previous release
2. Analyze root cause
3. Fix and re-test
4. Deploy hotfix
5. Communicate with stakeholders

---

## Communication & Stakeholders

### Stakeholder Updates

| Stakeholder | Frequency | Format |
|-----------|-----------|--------|
| Project sponsor (TAFE) | Monthly | Status report + demo |
| Development team | Weekly | Standup + sprint review |
| End users (facilities) | Quarterly | Training + feedback session |
| IT operations | As needed | Deployment coordination |

### Change Log

Document all changes in:
- **GitHub releases** - For technical audience
- **Changelog.md** - For user-facing updates
- **Release notes** - For stakeholder communication

---

## Related Documentation

- [Project Overview](./project-overview-pdr.md) - Business requirements
- [System Architecture](./system-architecture.md) - Technical design
- [Code Standards](./code-standards.md) - Development guidelines
- [Deployment Guide](./deployment-guide.md) - Operations
