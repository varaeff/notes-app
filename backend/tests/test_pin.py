import time


def _auth(client, username="user1", password="pw123456"):
    client.post("/api/auth/register", json={"username": username, "password": password})
    r = client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_pin_puts_note_on_top(client):
    h = _auth(client)
    client.post("/api/notes", headers=h, json={"title": "oldest", "content": ""})
    time.sleep(0.01)
    mid = client.post("/api/notes", headers=h, json={"title": "middle", "content": ""}).json()["id"]
    time.sleep(0.01)
    client.post("/api/notes", headers=h, json={"title": "newest", "content": ""})

    # Without pin, newest comes first (ordered by updated_at desc).
    r = client.get("/api/notes", headers=h)
    titles = [n["title"] for n in r.json()["items"]]
    assert titles == ["newest", "middle", "oldest"]

    # Pin the middle one → it jumps to the top.
    assert client.post(f"/api/notes/{mid}/pin", headers=h).status_code == 200
    r = client.get("/api/notes", headers=h)
    titles = [n["title"] for n in r.json()["items"]]
    assert titles[0] == "middle"

    # Unpin removes pin priority. The note can still be first because unpin updates updated_at.
    assert client.post(f"/api/notes/{mid}/unpin", headers=h).status_code == 200
    r = client.get("/api/notes", headers=h)
    items = r.json()["items"]
    middle = next(n for n in items if n["id"] == mid)
    assert middle["pinned_at"] is None
    assert all(n["pinned_at"] is None for n in items)


def test_pin_isolation(client):
    h1 = _auth(client, "alice", "pw123456")
    h2 = _auth(client, "eve", "pw123456")
    nid = client.post("/api/notes", headers=h1, json={"title": "A", "content": ""}).json()["id"]
    assert client.post(f"/api/notes/{nid}/pin", headers=h2).status_code == 404
