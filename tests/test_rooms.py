from common.models import RoleEnum

ADMIN_PAYLOAD = {
    "name": "Admin",
    "username": "admin",
    "email": "admin@example.com",
    "password": "Passw0rd!",
    "role": RoleEnum.ADMIN.value,
}


def auth_header(users_client, username: str, password: str) -> dict[str, str]:
    response = users_client.post(
        "/users/login",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def setup_admin(users_client):
    users_client.post("/users/register", json=ADMIN_PAYLOAD)


def test_room_crud(users_client, rooms_client):
    setup_admin(users_client)
    headers = auth_header(users_client, "admin", "Passw0rd!")

    create_resp = rooms_client.post(
        "/rooms",
        json={
            "name": "Board Room",
            "capacity": 10,
            "equipment": ["tv", "whiteboard"],
            "location": "Floor 1",
            "is_active": True,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    room_id = create_resp.json()["id"]

    list_resp = rooms_client.get("/rooms?capacity=5", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    status_resp = rooms_client.get(f"/rooms/{room_id}/status", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "available"
    cached_resp = rooms_client.get(f"/rooms/{room_id}/status", headers=headers)
    assert cached_resp.status_code == 200
    assert cached_resp.json()["checked_at"] == status_resp.json()["checked_at"]

    refresh_resp = rooms_client.get(f"/rooms/{room_id}/status?force_refresh=true", headers=headers)
    assert refresh_resp.status_code == 200
    assert refresh_resp.json()["checked_at"] != status_resp.json()["checked_at"]
