from common.models import RoleEnum

ADMIN_PAYLOAD = {
    "name": "Admin",
    "username": "admin",
    "email": "admin@example.com",
    "password": "Passw0rd!",
    "role": RoleEnum.ADMIN.value,
}


def auth_header(client, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/users/login",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_user_registration_and_listing(users_client):
    admin_resp = users_client.post("/users/register", json=ADMIN_PAYLOAD)
    assert admin_resp.status_code == 201

    user_resp = users_client.post(
        "/users/register",
        json={
            "name": "Jane",
            "username": "jane",
            "email": "jane@example.com",
            "password": "Passw0rd!",
        },
    )
    assert user_resp.status_code == 201

    headers = auth_header(users_client, "admin", "Passw0rd!")
    list_resp = users_client.get("/users", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 2


def test_user_update_self(users_client):
    users_client.post("/users/register", json=ADMIN_PAYLOAD)
    headers = auth_header(users_client, "admin", "Passw0rd!")

    update_resp = users_client.put(
        "/users/admin",
        json={"name": "Admin Updated"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Admin Updated"
