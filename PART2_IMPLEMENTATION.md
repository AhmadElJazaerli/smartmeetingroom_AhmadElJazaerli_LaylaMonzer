# Smart Meeting Room System - Part 2 Implementation

## Overview
This document describes the implementation of Part 2 features:
1. **Analytics and Insights** - Real-time dashboards with Grafana and comprehensive data analytics
2. **Multi-Factor Authentication (MFA)** - TOTP-based MFA for sensitive operations

---

## 1. Analytics and Insights

### Architecture
- **Analytics Service**: Dedicated microservice for data aggregation and analysis
- **Prometheus**: Metrics collection from all services
- **Grafana**: Real-time dashboards and visualizations

### Analytics Service Endpoints

#### Dashboard Overview
```
GET /analytics/dashboard/overview
```
Returns comprehensive system statistics including:
- Total users (active/inactive)
- Total rooms (available/unavailable)
- Booking statistics (total/confirmed/cancelled/today)
- Review statistics (total/average rating)

**Response Example:**
```json
{
  "users": {"total": 150, "active": 142, "inactive": 8},
  "rooms": {"total": 25, "available": 20, "unavailable": 5},
  "bookings": {"total": 1250, "confirmed": 1180, "cancelled": 70, "today": 45},
  "reviews": {"total": 856, "average_rating": 4.35}
}
```

#### Booking Frequency
```
GET /analytics/bookings/frequency?period=daily&days=30
```
Returns booking frequency over time (daily/weekly/monthly).

#### Bookings by Room
```
GET /analytics/bookings/by-room?days=30
```
Returns booking count per room for the specified period.

#### Top Users by Bookings
```
GET /analytics/bookings/by-user?days=30&limit=10
```
Returns top users ranked by booking activity.

#### Room Ratings
```
GET /analytics/rooms/ratings
```
Returns average ratings and review counts for all rooms.

#### Room Utilization
```
GET /analytics/rooms/utilization?days=30
```
Calculates room utilization rate (percentage of time booked vs available).

**Response Example:**
```json
{
  "period_days": 30,
  "available_hours_per_room": 240,
  "rooms": [
    {
      "room_id": 1,
      "room_name": "Conference Room A",
      "booking_count": 45,
      "total_hours_booked": 120.5,
      "utilization_percentage": 50.21
    }
  ]
}
```

#### User Activity
```
GET /analytics/users/activity?days=30
```
Returns user activity statistics including role distribution.

#### Monthly Trends
```
GET /analytics/trends/monthly?months=6
```
Returns monthly trends for bookings and reviews.

#### Peak Hours Analysis
```
GET /analytics/peak-hours?days=30
```
Identifies peak booking hours throughout the day.

### Prometheus Metrics

All services expose metrics at `/metrics` endpoint:
- `http_requests_total`: Total HTTP requests
- `http_request_duration_seconds`: Request duration histogram
- `http_requests_in_progress`: Current requests in progress

### Grafana Dashboards

#### System Overview Dashboard
- HTTP requests per second by service
- Request duration (95th percentile)
- Service health status
- HTTP status code distribution
- Error rates

#### Business Analytics Dashboard
- Total bookings (last 24h)
- Active users
- Average room rating (gauge)
- Room utilization rate
- Booking frequency over time
- Top 10 most booked rooms
- Reviews created (daily)
- User activity by role
- Peak booking hours (heatmap)

### Access Grafana
1. URL: `http://localhost:3000`
2. Default credentials: `admin` / `admin`
3. Pre-configured dashboards will be available automatically

---

## 2. Multi-Factor Authentication (MFA)

### Overview
TOTP-based (Time-based One-Time Password) MFA implementation for sensitive operations.

### Features
- QR code generation for authenticator apps (Google Authenticator, Authy, etc.)
- Optional MFA - users can choose to enable it
- Required for sensitive operations when enabled:
  - Deleting users
  - Canceling bookings
  - Other admin operations

### MFA Endpoints

#### Check MFA Status
```
GET /auth/mfa/status
Authorization: Bearer <token>
```

**Response:**
```json
{
  "mfa_enabled": true,
  "username": "john_doe"
}
```

#### Setup MFA
```
POST /auth/mfa/setup
Authorization: Bearer <token>
```

**Response:**
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code": "data:image/png;base64,...",
  "uri": "otpauth://totp/SmartMeetingRoom:john_doe?secret=JBSWY3DPEHPK3PXP&issuer=SmartMeetingRoom"
}
```

Steps:
1. Scan QR code with authenticator app
2. Or manually enter the secret key
3. Verify setup with a code

#### Enable MFA
```
POST /auth/mfa/enable
Authorization: Bearer <token>
Content-Type: application/json

{
  "code": "123456"
}
```

Verifies the TOTP code and enables MFA.

#### Disable MFA
```
POST /auth/mfa/disable
Authorization: Bearer <token>
Content-Type: application/json

{
  "code": "123456"
}
```

Requires valid TOTP code to disable MFA.

#### Login with MFA
```
POST /auth/login-mfa
Content-Type: application/json

{
  "username": "john_doe",
  "password": "password123",
  "mfa_code": "123456"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### Using MFA for Sensitive Operations

When MFA is enabled, sensitive operations require the `X-MFA-Code` header:

#### Example: Delete User
```bash
DELETE /users/username
Authorization: Bearer <token>
X-MFA-Code: 123456
```

#### Example: Cancel Booking
```bash
DELETE /bookings/123
Authorization: Bearer <token>
X-MFA-Code: 123456
```

### MFA Workflow

1. **User enables MFA:**
   ```
   POST /auth/mfa/setup → Get QR code
   Scan with authenticator app
   POST /auth/mfa/enable {"code": "123456"} → MFA enabled
   ```

2. **Login with MFA:**
   ```
   POST /auth/login → Error: "MFA required"
   POST /auth/login-mfa {"username": "...", "password": "...", "mfa_code": "123456"}
   ```

3. **Perform sensitive operation:**
   ```
   DELETE /users/someuser
   Headers:
     Authorization: Bearer <token>
     X-MFA-Code: 123456
   ```

---

## Running the System

### Prerequisites
- Docker and Docker Compose
- Python 3.10+ (for local development)

### Start All Services
```bash
docker-compose up -d
```

### Services and Ports
- **Users Service**: http://localhost:8001
- **Rooms Service**: http://localhost:8002
- **Bookings Service**: http://localhost:8003
- **Reviews Service**: http://localhost:8004
- **Analytics Service**: http://localhost:8005
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
- **PostgreSQL**: localhost:5432

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f users_service
docker-compose logs -f analytics_service
```

### Stop Services
```bash
docker-compose down
```

### Rebuild After Code Changes
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

---

## Testing Analytics

### Access Analytics API
```bash
# Get dashboard overview
curl -H "Authorization: Bearer <token>" \
  http://localhost:8005/analytics/dashboard/overview

# Get booking frequency
curl -H "Authorization: Bearer <token>" \
  http://localhost:8005/analytics/bookings/frequency?days=30

# Get room utilization
curl -H "Authorization: Bearer <token>" \
  http://localhost:8005/analytics/rooms/utilization?days=30
```

### Access Grafana
1. Navigate to http://localhost:3000
2. Login with `admin` / `admin`
3. View pre-configured dashboards:
   - System Overview
   - Business Analytics

---

## Testing MFA

### Setup MFA for a User
```bash
# 1. Register and login
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","username":"testuser","email":"test@example.com","password":"password123","role":"admin"}'

curl -X POST http://localhost:8001/auth/login \
  -d "username=testuser&password=password123"

# Save the token
TOKEN="<access_token_from_response>"

# 2. Setup MFA
curl -X POST http://localhost:8001/auth/mfa/setup \
  -H "Authorization: Bearer $TOKEN"

# Scan the QR code or use the secret in an authenticator app

# 3. Enable MFA with code from authenticator
curl -X POST http://localhost:8001/auth/mfa/enable \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"code":"<6-digit-code>"}'

# 4. Test MFA login
curl -X POST http://localhost:8001/auth/login-mfa \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123","mfa_code":"<6-digit-code>"}'

# 5. Test sensitive operation with MFA
curl -X DELETE http://localhost:8001/users/someuser \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-MFA-Code: <6-digit-code>"
```

---

## Security Considerations

1. **MFA Secret Storage**: Encrypted in database
2. **JWT Tokens**: Short-lived tokens with configurable expiration
3. **HTTPS**: Use HTTPS in production
4. **Environment Variables**: Change default secrets in production
5. **Database**: Use strong passwords and restrict network access

---

## Monitoring and Observability

### Prometheus Queries
Access http://localhost:9090 and try these queries:

```promql
# Request rate per service
rate(http_requests_total[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Service availability
up{job=~".*_service"}
```

### Grafana Alerts
Configure alerts in Grafana for:
- High error rates
- Service downtime
- High response times
- Low room utilization

---

## Performance Optimization

1. **Database Indexing**: All foreign keys and frequently queried fields are indexed
2. **Connection Pooling**: SQLAlchemy connection pools for each service
3. **Caching**: Consider adding Redis for frequently accessed analytics data
4. **Query Optimization**: Analytics queries use aggregations and proper filtering

---

## Future Enhancements

1. **Real-time Updates**: WebSocket support for live dashboard updates
2. **Custom Reports**: User-defined report generation
3. **Email Alerts**: Automated alerts for booking confirmations, MFA setup, etc.
4. **Backup MFA Codes**: One-time backup codes for account recovery
5. **SMS MFA**: Alternative to TOTP for MFA
6. **API Rate Limiting**: Protect against abuse
7. **Advanced Analytics**: Machine learning for booking predictions

---

## Troubleshooting

### Services won't start
```bash
# Check logs
docker-compose logs

# Check database health
docker-compose ps db

# Restart specific service
docker-compose restart users_service
```

### Grafana dashboards not loading
```bash
# Check Prometheus is running
curl http://localhost:9090/-/healthy

# Check Grafana logs
docker-compose logs grafana
```

### MFA codes not working
- Ensure device time is synchronized (NTP)
- TOTP requires accurate time
- Check authenticator app is using the correct secret

---

## Summary

Part 2 implementation provides:

✅ **Analytics Service** with 10+ comprehensive endpoints
✅ **Prometheus** metrics collection from all services
✅ **Grafana** dashboards (System Overview & Business Analytics)
✅ **MFA with TOTP** for enhanced security
✅ **Sensitive operations protection** with MFA verification
✅ **Real-time monitoring** and alerting capabilities
✅ **Production-ready** Docker Compose configuration

All requirements for Part 2 tasks 5 and 6 are fully implemented and ready for deployment.
