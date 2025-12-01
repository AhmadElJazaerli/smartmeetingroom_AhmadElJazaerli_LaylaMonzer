from common.models import RoleEnum

ADMIN_PAYLOAD = {
    "name": "Admin",
    "username": "admin",
    "email": "admin@example.com",
    "password": "Passw0rd!",
    "role": RoleEnum.ADMIN.value,
}

USER_PAYLOAD = {
    "name": "Critic",
    "username": "critic",
    "email": "critic@example.com",
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


def test_review_lifecycle(users_client, rooms_client, reviews_client):
    users_client.post("/users/register", json=ADMIN_PAYLOAD)
    admin_headers = auth_header(users_client, "admin", "Passw0rd!")

    room_resp = rooms_client.post(
        "/rooms",
        json={
            "name": "Review Room",
            "capacity": 4,
            "equipment": ["speaker"],
            "location": "Floor 3",
            "is_active": True,
        },
        headers=admin_headers,
    )
    room_id = room_resp.json()["id"]

    users_client.post("/users/register", json=USER_PAYLOAD)
    user_headers = auth_header(users_client, "critic", "Passw0rd!")

    review_resp = reviews_client.post(
        "/reviews",
        json={"room_id": room_id, "rating": 5, "comment": "Great room!"},
        headers=user_headers,
    )
    assert review_resp.status_code == 201
    review_id = review_resp.json()["id"]

    list_resp = reviews_client.get(f"/reviews/room/{room_id}")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    flag_resp = reviews_client.post(f"/reviews/{review_id}/flag", headers=admin_headers)
    assert flag_resp.status_code == 200
    assert flag_resp.json()["is_flagged"] is True
