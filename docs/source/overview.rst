Overview
========

The Smart Meeting Room & Management System provides four FastAPI-based services that expose independent REST APIs for managing users, rooms, bookings, and reviews.

Architecture
------------

* **Users Service** – Authentication, profile management, RBAC, booking history.
* **Rooms Service** – Inventory, capacity, equipment metadata, availability lookup.
* **Bookings Service** – Scheduling, conflict detection, lifecycle management.
* **Reviews Service** – Feedback submission, moderation, sanitization.

All services share a PostgreSQL database instance and communicate via internal HTTP calls authenticated with JWT bearer tokens or service API keys.

Part II Enhancements
--------------------

* **Adaptive rate limiting** via SlowAPI protects every public endpoint with per-service defaults plus stricter caps on burst-heavy operations such as authentication and booking creation.
* **Audit logging middleware** records every request/response pair with correlation IDs inside the ``logs/`` directory, enabling compliance review and anomaly detection.
* **Room availability caching** adds a TTL cache (default 60 seconds) for ``GET /rooms/{id}/status`` responses with manual invalidation hooks that fire when rooms are created, updated, or deleted. Clients may pass ``force_refresh=true`` to bypass cached data.
* **Analytics APIs** in the Bookings service expose room popularity and user activity leaderboards to admins/facility managers, powering dashboards without extra BI tooling.
