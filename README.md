# Smart Meeting Room & Management System

Backend implementation for the Software Tools Lab final project (Fall 2025-2026). The system exposes four FastAPI-based microservices (Users, Rooms, Bookings, Reviews) plus shared infrastructure for authentication, RBAC, and persistence.

## Features
- JWT authentication and role-based access control covering Admin, Regular User, Facility Manager, Moderator, Auditor, and Service account roles.
- CRUD APIs for managing users, meeting rooms, bookings, and reviews with cross-service coordination.
- Validation/sanitization of user inputs plus moderation workflows for reviews.
- SlowAPI-backed rate limiting and audit logging middleware across every service.
- TTL caching for room availability lookups with manual invalidation hooks.
- Analytics endpoints for room popularity and user activity to support dashboards.
- Shared PostgreSQL database (Dockerized) with SQLAlchemy models and Alembic migrations scaffold.
- Pytest suites per service, Postman collection, and Sphinx documentation.
- Dockerfiles for each service and a docker-compose stack that wires services, database, and networking.
- Profiling scripts and coverage configuration for performance/memory instrumentation.

## Quick start
```bash
# install deps
pip install -e .[dev]

# run unit tests
pytest

# build docs (includes overview of enhancements)
(cd docs && make html)

# run services locally (example: users service)
uvicorn services.users.app:app --reload --port 8001
```

For complete instructions (Docker, env variables, docs build, profiling, and API reference), see `docs/build/html/index.html` after running `make html` under `docs/`.


To run using docker, please have docker desktop already installed and open, then run docker compose up , this will get all 4 services running no need to do any of the previous steps.