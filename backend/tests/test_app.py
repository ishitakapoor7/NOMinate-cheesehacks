def test_index_ok(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.get_json()["message"] == "NOMinate API is running."


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
