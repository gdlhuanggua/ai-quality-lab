import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def test_crud_flow(client, asset_body):
    response = client.post("/api/assets", json=asset_body)
    assert response.status_code == 201
    asset = response.json()
    asset_id = asset["id"]
    assert {key: asset[key] for key in asset_body} == asset_body
    assert client.get(f"/api/assets/{asset_id}").json() == asset
    updated = {**asset_body, "name": "New name", "owner": "new-team"}
    assert client.put(f"/api/assets/{asset_id}", json=updated).json()["name"] == "New name"
    assert client.delete(f"/api/assets/{asset_id}").status_code == 204
    assert client.get(f"/api/assets/{asset_id}").status_code == 404
    assert client.get("/api/assets").json()["total"] == 0


@pytest.mark.parametrize("name", ["A", "a" * 40, " Test "])
def test_name_valid_boundaries(client, asset_body, name):
    response = client.post("/api/assets", json={**asset_body, "name": name})
    assert response.status_code == 201
    assert response.json()["name"] == name.strip()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", ""),
        ("name", "   "),
        ("name", "a" * 41),
        ("name", 123),
        ("name", None),
        ("owner", ""),
        ("owner", " " * 5),
        ("owner", "a" * 31),
        ("owner", []),
        ("asset_code", "AB"),
        ("asset_code", "A" * 33),
        ("asset_code", "data-001"),
        ("asset_code", " BAD-001 "),
        ("asset_code", "A';DROP TABLE assets;--"),
        ("asset_code", "123"),
        ("asset_code", None),
        ("sensitivity", "secret"),
        ("sensitivity", "PUBLIC"),
        ("sensitivity", False),
    ],
)
def test_invalid_fields_rejected(client, asset_body, field, value):
    response = client.post("/api/assets", json={**asset_body, field: value})
    assert response.status_code == 422
    assert client.get("/api/assets").json()["total"] == 0


@pytest.mark.parametrize("code", ["ABC", "A" * 32, "DATA-001"])
def test_code_valid_boundaries(client, asset_body, code):
    assert client.post("/api/assets", json={**asset_body, "asset_code": code}).status_code == 201


@pytest.mark.parametrize("sensitivity", ["public", "internal", "confidential"])
def test_sensitivity_enum(client, asset_body, sensitivity):
    assert client.post("/api/assets", json={**asset_body, "sensitivity": sensitivity}).status_code == 201


@pytest.mark.parametrize("field", ["asset_code", "name", "owner", "sensitivity"])
def test_missing_fields(client, asset_body, field):
    asset_body.pop(field)
    assert client.post("/api/assets", json=asset_body).status_code == 422


def test_unknown_field_rejected(client, asset_body):
    assert client.post("/api/assets", json={**asset_body, "unexpected": True}).status_code == 422


def test_duplicate_code(client, asset_body):
    assert client.post("/api/assets", json=asset_body).status_code == 201
    assert client.post("/api/assets", json=asset_body).status_code == 409
    assert client.get("/api/assets").json()["total"] == 1


def test_update_conflict_does_not_change_original(client, asset_body):
    first = client.post("/api/assets", json=asset_body).json()
    second_body = {**asset_body, "asset_code": "DATA-002", "name": "Second"}
    second = client.post("/api/assets", json=second_body).json()
    response = client.put(f"/api/assets/{second['id']}", json=asset_body)
    assert response.status_code == 409
    assert client.get(f"/api/assets/{second['id']}").json() == second
    assert client.get(f"/api/assets/{first['id']}").json() == first


def test_invalid_update_keeps_record(client, asset_body):
    asset = client.post("/api/assets", json=asset_body).json()
    assert client.put(f"/api/assets/{asset['id']}", json={**asset_body, "name": ""}).status_code == 422
    assert client.get(f"/api/assets/{asset['id']}").json() == asset


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_not_found(client, asset_body, method):
    kwargs = {"json": asset_body} if method == "put" else {}
    assert getattr(client, method)("/api/assets/999", **kwargs).status_code == 404


@pytest.mark.parametrize("path", ["/api/assets/0", "/api/assets/-1", "/api/assets/not-a-number"])
def test_invalid_id(client, path):
    assert client.get(path).status_code == 422


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "q=" + "a" * 81])
def test_invalid_pagination(client, query):
    assert client.get("/api/assets?" + query).status_code == 422


def test_search_and_pagination(client, asset_body):
    for index in range(3):
        client.post("/api/assets", json={**asset_body, "asset_code": f"CODE-{index}"})
    result = client.get("/api/assets?limit=1&offset=1").json()
    assert result["total"] == 3
    assert len(result["items"]) == 1
    assert result["items"][0]["asset_code"] == "CODE-1"
    assert client.get("/api/assets?q=CODE-2").json()["total"] == 1
    assert client.get("/api/assets?q=demo-team").json()["total"] == 3


@pytest.mark.parametrize("query", ["%", "_", "' OR 1=1 --", "\\"])
def test_search_does_not_treat_input_as_sql_or_wildcard(client, asset_body, query):
    client.post("/api/assets", json=asset_body)
    assert client.get("/api/assets", params={"q": query}).json()["total"] == 0
    assert client.get("/api/assets").json()["total"] == 1


def test_restart_persists_data(tmp_path, asset_body):
    path = tmp_path / "persist.db"
    with TestClient(create_app(path)) as first:
        first.post("/api/assets", json=asset_body)
    with TestClient(create_app(path)) as second:
        assert second.get("/api/assets").json()["total"] == 1


def test_health_and_static_files(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/").status_code == 200
    assert "AI Quality Lab" in client.get("/").text
    for path in ["app.js", "styles.css", "lucide.min.js"]:
        assert client.get("/static/" + path).status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_json_syntax_error(client):
    assert client.post("/api/assets", content="{", headers={"Content-Type": "application/json"}).status_code == 422
