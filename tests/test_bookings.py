from datetime import datetime, timedelta

from common.models import RoleEnum

ADMIN_PAYLOAD = {
    "name": "Admin",
    "username": "admin",
    "email": "admin@example.com",
    "password": "Passw0rd!",
    "role": RoleEnum.ADMIN.value,
}

USER_PAYLOAD = {
    "name": "User",
    "username": "user1",
    "email": "user1@example.com",
    "password": "Passw0rd!",
}


def auth_header(users_client, username: str, password: str) -> dict[str, str]:
    response = users_client.post(
        "/users/login",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_booking_flow(users_client, rooms_client, bookings_client):
    users_client.post("/users/register", json=ADMIN_PAYLOAD)
    admin_headers = auth_header(users_client, "admin", "Passw0rd!")

    room_resp = rooms_client.post(
        "/rooms",
        json={
            "name": "Focus Room",
            "capacity": 6,
            "equipment": ["tv"],
            "location": "Floor 2",
            "is_active": True,
        },
        headers=admin_headers,
    )
    room_id = room_resp.json()["id"]

    users_client.post("/users/register", json=USER_PAYLOAD)
    user_headers = auth_header(users_client, "user1", "Passw0rd!")

    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=2)

    booking_resp = bookings_client.post(
        "/bookings",
        json={
            "room_id": room_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "status": "confirmed",
        },
        headers=user_headers,
    )
    assert booking_resp.status_code == 201

    availability = bookings_client.get(
        f"/bookings/availability?room_id={room_id}&start_time={(start_time + timedelta(hours=3)).isoformat()}&end_time={(end_time + timedelta(hours=4)).isoformat()}"
    )
    assert availability.status_code == 200
    assert availability.json()["available"] is True

    room_analytics = bookings_client.get("/analytics/rooms/popularity", headers=admin_headers)
    assert room_analytics.status_code == 200
    assert any(entry["room_id"] == room_id for entry in room_analytics.json())

    user_analytics = bookings_client.get("/analytics/users/activity", headers=admin_headers)
    assert user_analytics.status_code == 200
    assert any(entry["username"] == "user1" for entry in user_analytics.json())
