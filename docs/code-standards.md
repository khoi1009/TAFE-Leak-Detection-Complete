# Code Standards & Development Guidelines

**Version:** 2.1.2 | **Updated:** January 29, 2026

---

## Naming Conventions

### Python Files

**Standard:** kebab-case with descriptive names

```
✓ GOOD
  - model_1_realtime_simulation.py
  - false_alarm_patterns.py
  - components_map.py
  - action_log_viewer.py

✗ AVOID
  - ml.py (too vague)
  - utils2.py (ambiguous)
  - temp_script.py (temporary)
```

### Python Classes

**Standard:** PascalCase

```python
class UserRole(enum.Enum):
    admin = "admin"
    operator = "operator"

class Incident(Base):
    __tablename__ = "incidents"

class IncidentResponse(BaseModel):
    id: int
    school_name: str
```

### Python Functions & Variables

**Standard:** snake_case

```python
def get_current_user(token: str) -> User:
    """Extract user from JWT token."""
    pass

def calculate_confidence(signals: dict) -> float:
    """Multi-signal weighted scoring."""
    pass

incident_list = []
user_email = "operator@tafe.nsw.edu.au"
```

### Constants

**Standard:** UPPER_SNAKE_CASE

```python
# Backend
SECRET_KEY = "your-secret-key"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
DATABASE_URL = "sqlite+aiosqlite:///./leak_detection.db"
CORS_ORIGINS = ["http://localhost:8050", "http://localhost:8051"]

# Frontend
ML_THRESHOLD_ALERT = 70  # Confidence % to trigger alert
BASELINE_WINDOW_DAYS = 28
UPDATE_INTERVAL_SECONDS = 300  # Dashboard refresh
```

### Database Models

**Standard:** Singular, descriptive names

```python
__tablename__ = "users"       # ✓ Plural for multiple records
__tablename__ = "incidents"   # ✓ Plural for multiple records
__tablename__ = "action_logs" # ✓ Snake_case table names
```

---

## Code Organization

### Backend Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry
│   │
│   ├── api/                    # Route handlers
│   │   ├── __init__.py         # Router aggregation
│   │   ├── auth.py             # Auth endpoints
│   │   ├── incidents.py        # Incident endpoints
│   │   └── schools.py          # School endpoints
│   │
│   ├── core/                   # Core utilities
│   │   ├── __init__.py
│   │   ├── config.py           # Settings
│   │   ├── database.py         # DB setup
│   │   └── security.py         # Auth helpers
│   │
│   ├── models/                 # ORM models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── incident.py
│   │
│   └── services/               # Business logic (stub for future)
│       └── __init__.py
│
└── requirements.txt
```

### Frontend Project Structure

```
frontend/
├── app.py                      # Main dashboard entry
├── login_app.py                # Login portal
│
├── layout.py                   # Dashboard structure
├── callbacks.py                # Interactive logic
├── components.py               # Reusable UI components
├── components_map.py           # GIS map component
│
├── Model_1_realtime_simulation.py  # ML scoring engine
├── engine_fallback.py          # Demo mode fallback
│
├── data.py                     # Data loading
├── processing.py               # Data transformations
├── false_alarm_patterns.py     # Pattern learning
├── utils.py                    # Helper functions
├── config.py                   # Settings
│
├── assets/                     # Styling
│   ├── login-styles.css
│   ├── _design-system.css
│   └── _responsive.css
│
├── data/                       # Demo data
│   ├── demo_data.xlsx
│   ├── demo_school_mapping.csv
│   └── demo_schools_gis.json
│
└── requirements.txt
```

---

## Function & Method Standards

### Docstring Format

**Standard:** Google-style docstrings with type hints

```python
def create_incident(
    session: AsyncSession,
    school_name: str,
    confidence: float,
    signals: dict
) -> Incident:
    """
    Create a new leak incident record.

    Args:
        session: Async database session
        school_name: Name of the school
        confidence: Confidence score (0-100)
        signals: Signal breakdown {MNF, RESIDUAL, ...}

    Returns:
        Created Incident object

    Raises:
        ValueError: If confidence outside 0-100 range
        DatabaseError: If database write fails

    Example:
        >>> incident = await create_incident(
        ...     session, "ABC School", 78.5, signals_dict
        ... )
        >>> print(incident.id)
    """
    if not 0 <= confidence <= 100:
        raise ValueError("Confidence must be 0-100")

    incident = Incident(
        school_name=school_name,
        confidence=confidence,
        signals=signals
    )
    session.add(incident)
    await session.commit()
    return incident
```

### Error Handling

**Standard:** Structured exception handling with context

```python
# Backend - API errors
from fastapi import HTTPException, status

@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: int, session: AsyncSession):
    """Fetch single incident."""
    try:
        result = await session.execute(
            select(Incident).where(Incident.id == incident_id)
        )
        incident = result.scalar_one_or_none()

        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incident {incident_id} not found"
            )

        return incident

    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error retrieving incident"
        ) from e

# Frontend - Graceful degradation
try:
    response = requests.get(f"{API_URL}/incidents/")
    incidents = response.json()
except requests.exceptions.ConnectionError:
    print("⚠️ API unavailable, using demo data")
    incidents = load_demo_data()
```

### Type Hints

**Standard:** Always provide type hints for function signatures

```python
# ✓ GOOD - Clear types
def calculate_confidence(
    signals: dict[str, float]
) -> float:
    """Calculate weighted confidence score."""
    pass

def list_incidents(
    skip: int = 0,
    limit: int = 10,
    status: str | None = None
) -> list[IncidentResponse]:
    """List incidents with pagination."""
    pass

# ✗ AVOID - No type hints
def calculate_confidence(signals):
    pass

def list_incidents(skip, limit, status):
    pass
```

---

## Code Quality Standards

### Maximum File Size

**Standard:** Keep Python files <200 lines for optimal readability

| File Type | Soft Limit | Hard Limit | Rationale |
|-----------|-----------|-----------|-----------|
| API endpoint | 150 LOC | 200 LOC | Single concern |
| Component | 100 LOC | 150 LOC | Reusability |
| Utility module | 100 LOC | 200 LOC | Helper functions |
| Model | 50 LOC | 100 LOC | ORM classes |
| Main app file | 200 LOC | 300 LOC | Entry point OK |

**When to split:**
```
# ✗ TOO LARGE (250 LOC)
frontend/callbacks.py
  ├─ Override count: 50+ callbacks mixed

# ✓ SPLIT INTO
frontend/callbacks_incidents.py
  └─ Incident-related callbacks
frontend/callbacks_filters.py
  └─ Filter & search callbacks
frontend/callbacks_exports.py
  └─ Export & download callbacks
```

### Import Organization

**Standard:** Organized in groups with blank lines

```python
# 1. Standard library
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional

# 2. Third-party libraries
import pandas as pd
import numpy as np
from fastapi import FastAPI, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# 3. Local imports
from app.core.config import settings
from app.core.database import get_db
from app.models.incident import Incident

# ✗ AVOID: Mixed, unsorted imports
from typing import Optional
from fastapi import FastAPI
import pandas
from app.models.incident import Incident
import asyncio
```

### Comments & Docstrings

**Standard:** Clear, purposeful comments only

```python
# ✓ GOOD - Explains WHY
# Use 28-day window to account for weekly patterns
baseline_window = 28

# ✓ GOOD - Clarifies complex logic
# CUSUM control chart detects gradual shifts
# Reset if exceeds threshold (h=5)
cusum_score = calculate_cusum(data, h=5)

# ✗ AVOID - States the obvious
# Add 1 to i
i += 1

# ✗ AVOID - Outdated comments
# TODO: Fix this later (from 2023)
# HACK: Temporary workaround (still there after 6 months)
```

### Error Messages

**Standard:** Descriptive, actionable error messages

```python
# ✓ GOOD - Clear context
raise ValueError(
    "Confidence score must be 0-100. "
    f"Got {confidence}. Check signal calculations."
)

# ✓ GOOD - Actionable
raise HTTPException(
    status_code=400,
    detail="School 'XYZ' not found. Use /schools endpoint to list valid schools."
)

# ✗ AVOID - Vague
raise ValueError("Invalid value")
raise Exception("Error")
```

---

## Backend Patterns

### API Endpoint Pattern

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

router = APIRouter(prefix="/incidents", tags=["Incidents"])

class IncidentCreate(BaseModel):
    """Request schema."""
    property_id: str
    school_name: str
    confidence: float

class IncidentResponse(BaseModel):
    """Response schema."""
    id: int
    school_name: str
    confidence: float

    model_config = {"from_attributes": True}

@router.post("/", response_model=IncidentResponse, status_code=201)
async def create_incident(
    data: IncidentCreate,
    current_user = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Create new incident."""
    # Validate authorization
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create incidents"
        )

    # Create record
    incident = Incident(**data.model_dump())
    session.add(incident)
    await session.commit()
    await session.refresh(incident)

    return incident
```

### Dependency Injection

```python
# Define dependency
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db)
) -> User:
    """Extract and validate current user from token."""
    payload = verify_token(token)
    user_id = payload.get("sub")

    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user

# Use in endpoint
@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
```

### Database Query Pattern

```python
# ✓ GOOD - Efficient single query
result = await session.execute(
    select(Incident)
    .where(Incident.status == "open")
    .order_by(Incident.created_at.desc())
    .limit(10)
)
incidents = result.scalars().all()

# ✗ AVOID - N+1 query problem
incidents = await session.execute(select(Incident))
for incident in incidents.scalars():
    user = await session.get(User, incident.assigned_to)  # Repeated!
```

---

## Frontend Patterns

### Dash Callback Pattern

```python
import dash
from dash import dcc, html, Input, Output, State

@app.callback(
    Output("incidents-table", "data"),
    Input("filter-status", "value"),
    Input("filter-school", "value"),
    State("incidents-table", "data"),
)
def update_incidents(status_filter, school_filter, existing_data):
    """
    Update incident table based on filters.

    Args:
        status_filter: Selected status
        school_filter: School name pattern
        existing_data: Current table data

    Returns:
        Filtered list of incidents
    """
    try:
        # Fetch from API
        response = requests.get(
            f"{API_URL}/incidents/",
            params={
                "status": status_filter,
                "school_name": school_filter
            }
        )
        response.raise_for_status()

        incidents = response.json()["items"]
        return [
            {
                "id": inc["id"],
                "school": inc["school_name"],
                "confidence": f"{inc['confidence']:.1f}%"
            }
            for inc in incidents
        ]

    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error fetching incidents: {e}")
        return existing_data or []
```

### Component Pattern

```python
def create_kpi_card(title: str, value: str, icon: str):
    """
    Create reusable KPI card component.

    Args:
        title: Card title
        value: Main value to display
        icon: Emoji or icon name

    Returns:
        Dash div component
    """
    return html.Div(
        [
            html.Div(icon, className="kpi-icon"),
            html.H3(title, className="kpi-title"),
            html.Div(value, className="kpi-value")
        ],
        className="kpi-card"
    )

# Usage
kpi_row = html.Div(
    [
        create_kpi_card("Total Incidents", "42", "📊"),
        create_kpi_card("Avg Confidence", "78.5%", "📈"),
        create_kpi_card("Schools Affected", "12", "🏫")
    ],
    className="kpi-row"
)
```

---

## Testing Standards

### Backend Testing

```python
# tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_login_success():
    """Test successful login."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@tafe.nsw.edu.au", "password": "admin123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_password():
    """Test login with wrong password."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@tafe.nsw.edu.au", "password": "wrong"}
    )
    assert response.status_code == 401
```

### Frontend Testing

```python
# test_pattern_matching.py
import unittest
from false_alarm_patterns import PatternMatcher

class TestPatternMatching(unittest.TestCase):
    def setUp(self):
        self.matcher = PatternMatcher()

    def test_pattern_detection(self):
        """Test detection of known false alarm pattern."""
        pattern = {
            "school": "ABC School",
            "time_of_day": "weekday_morning",
            "duration": 30  # minutes
        }
        self.matcher.learn_pattern(pattern)

        test_pattern = {
            "school": "ABC School",
            "time_of_day": "weekday_morning",
            "duration": 28
        }
        is_false_alarm = self.matcher.is_false_alarm(test_pattern)
        self.assertTrue(is_false_alarm)
```

---

## Git & Commit Standards

### Conventional Commits

**Format:** `type(scope): description`

```
feat(auth): add JWT token refresh endpoint
fix(incidents): prevent duplicate incident cards by deduping on site_id
docs(architecture): add system design diagrams
test(backend): add auth endpoint tests
refactor(ml-engine): extract signal calculation into separate module
style(frontend): format CSS according to style guide
chore(deps): upgrade fastapi to 0.110.0
```

### Commit Message Best Practices

```
✓ GOOD
feat(auth): add refresh token endpoint

Allow users to extend their session by refreshing
expired access tokens without re-logging in.

- Implement POST /auth/refresh endpoint
- Add refresh token validation logic
- Update token response schema

✗ AVOID
- "fix bug" (too vague)
- "update stuff" (no context)
- "WIP" (incomplete)
- Multiple unrelated changes in one commit
```

### Branch Naming

```
feature/auth-refresh-token
bugfix/duplicate-incident-cards
docs/system-architecture
test/add-backend-tests
```

---

## Security Standards

### Password Handling

```python
# ✓ CORRECT - Always hash
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hashing
hashed = pwd_context.hash("user_password")
db.password_hash = hashed

# Verification
is_valid = pwd_context.verify("user_password", db.password_hash)

# ✗ WRONG - Never store plaintext
db.password = user_input  # DANGEROUS!
```

### Token Handling

```python
# ✓ CORRECT - Sign with SECRET_KEY
from datetime import datetime, timedelta
from jose import jwt

def create_access_token(data: dict, expires_in: int = 30):
    expire = datetime.utcnow() + timedelta(minutes=expires_in)
    data.update({"exp": expire})
    token = jwt.encode(data, settings.SECRET_KEY, algorithm="HS256")
    return token

# ✗ WRONG - Hardcoded secret
token = jwt.encode(data, "secret123", algorithm="HS256")

# ✗ WRONG - No expiration
token = jwt.encode(data, SECRET_KEY)  # Never expires!
```

### Environment Variables

```
✓ CORRECT - Sensitive data in .env
# .env (not in git)
SECRET_KEY=actual-production-key
DATABASE_URL=postgresql://user:password@host/db

# config.py
settings.SECRET_KEY  # Loaded from .env

✗ WRONG - Hardcoded secrets
SECRET_KEY = "exposed-key"  # In source code!
PASSWORD = "admin123"  # In git history!
```

---

## Performance Optimization

### Query Optimization

```python
# ✗ SLOW - Filters after fetching all
incidents = await session.execute(select(Incident))
filtered = [i for i in incidents if i.status == "open"]

# ✓ FAST - Filter in database
result = await session.execute(
    select(Incident).where(Incident.status == "open")
)
incidents = result.scalars().all()
```

### Caching

```python
# Frontend - Cache API responses
from functools import lru_cache

@lru_cache(maxsize=128)
def get_schools():
    """Cache school list (static data)."""
    response = requests.get(f"{API_URL}/schools/")
    return response.json()

# Dashboard - Cache for 5 minutes
stats_cache = {"data": None, "timestamp": None}

def get_stats():
    now = time.time()
    if stats_cache["timestamp"] and (now - stats_cache["timestamp"]) < 300:
        return stats_cache["data"]

    response = requests.get(f"{API_URL}/incidents/stats")
    stats_cache["data"] = response.json()
    stats_cache["timestamp"] = now
    return stats_cache["data"]
```

---

## Related Documentation

- [Project Overview](./project-overview-pdr.md) - Requirements & goals
- [System Architecture](./system-architecture.md) - Design & data flow
- [Codebase Summary](./codebase-summary.md) - File organization
- [Deployment Guide](./deployment-guide.md) - Setup & operations
