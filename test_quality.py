import pytest


def test_synthetic_example_has_expected_issues(client):
    records = client.get("/api/examples/quality").json()
    response = client.post("/api/quality/check", json={"records": records})
    assert response.status_code == 200
    report = response.json()
    assert report["total"] == 8
    assert report["valid"] == 2
    assert report["invalid"] == 6
    assert report["valid_rate"] == 0.25
    assert "Duplicate" in report["rows"][2]["issues"][0]["message"]
    assert client.get("/api/assets").json()["total"] == 0


def test_both_duplicate_rows_flagged(client, asset_body):
    report = client.post("/api/quality/check", json={"records": [asset_body, asset_body]}).json()
    assert report["invalid"] == 2
    assert all(any(issue["message"] == "Duplicate asset_code" for issue in row["issues"]) for row in report["rows"])


@pytest.mark.parametrize("invalid_code", [None, 123, [], {}])
def test_unhashable_and_non_string_codes_do_not_crash(client, asset_body, invalid_code):
    response = client.post("/api/quality/check", json={"records": [{**asset_body, "asset_code": invalid_code}]})
    assert response.status_code == 200
    assert response.json()["invalid"] == 1


@pytest.mark.parametrize("records", [[], [None], ["text"], [{}] * 1001])
def test_bad_quality_request_rejected(client, records):
    assert client.post("/api/quality/check", json={"records": records}).status_code == 422


def test_quality_covers_extra_fields_and_missing_fields(client, asset_body):
    del asset_body["owner"]
    asset_body["unexpected"] = "value"
    report = client.post("/api/quality/check", json={"records": [asset_body]}).json()
    assert {issue["field"] for issue in report["rows"][0]["issues"]} == {"owner", "unexpected"}


def test_example_path_is_whitelisted(client):
    assert client.get("/api/examples/not-found").status_code == 422
