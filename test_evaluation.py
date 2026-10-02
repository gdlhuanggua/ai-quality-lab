from copy import deepcopy

import pytest


def sample_cases(client):
    return client.get("/api/examples/cases").json()


def test_demo_results_and_metrics(client):
    response = client.post("/api/cases/evaluate", json={"cases": sample_cases(client)})
    assert response.status_code == 200
    report = response.json()
    assert (report["total"], report["schema_valid"], report["duplicates"]) == (11, 10, 1)
    assert (report["executed"], report["passed"], report["failed"]) == (9, 8, 1)
    assert report["schema_valid_rate"] == 0.9091
    assert report["assertion_pass_rate"] == 0.8889
    assert report["scenario_coverage"] == 1.0
    assert len(report["covered_scenarios"]) == 8
    assert report["results"][9]["status"] == "rejected"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("method", "DELETE"),
        ("path", "https://example.com/api/assets"),
        ("path", "/api/cases/evaluate"),
        ("expected_status", "201"),
        ("expected_status", 201.0),
        ("expected_status", 200),
        ("body", "print('malicious')"),
        ("scenario", "invented_scenario"),
        ("expected_fields", []),
        ("name", ""),
    ],
)
def test_bad_case_schema_rejected_without_execution(client, field, value):
    case = deepcopy(sample_cases(client)[0])
    case[field] = value
    response = client.post("/api/cases/evaluate", json={"cases": [case]})
    assert response.status_code == 200
    report = response.json()
    assert report["executed"] == 0
    assert report["schema_valid_rate"] == 0
    assert report["assertion_pass_rate"] is None
    assert report["scenario_coverage"] == 0


@pytest.mark.parametrize("raw", [None, "text", 123, [], {}, {"name": "<script>alert(1)</script>"}])
def test_non_case_values_report_rejections(client, raw):
    report = client.post("/api/cases/evaluate", json={"cases": [raw]}).json()
    assert report["results"][0]["status"] == "rejected"


def test_extra_top_level_case_field_rejected(client):
    case = {**sample_cases(client)[0], "code": "malicious"}
    report = client.post("/api/cases/evaluate", json={"cases": [case]}).json()
    assert report["executed"] == 0


def test_case_execution_does_not_touch_application_data(client, asset_body):
    client.post("/api/assets", json=asset_body)
    before = client.get("/api/assets").json()
    for _ in range(2):
        report = client.post("/api/cases/evaluate", json={"cases": sample_cases(client)}).json()
        assert report["passed"] == 8
    assert client.get("/api/assets").json() == before


def test_two_cases_with_same_code_get_independent_databases(client):
    case = sample_cases(client)[0]
    other = deepcopy(case)
    other["body"]["name"] = "Different payload"
    report = client.post("/api/cases/evaluate", json={"cases": [case, other]}).json()
    assert report["executed"] == 2
    assert report["passed"] == 2


def test_duplicate_fixture_is_part_of_request_identity(client):
    duplicate = sample_cases(client)[7]
    valid = deepcopy(duplicate)
    valid["scenario"] = "valid_create"
    valid["expected_status"] = 201
    report = client.post("/api/cases/evaluate", json={"cases": [valid, duplicate]}).json()
    assert report["duplicates"] == 0
    assert report["passed"] == 2


def test_duplicate_request_order_independent_keys(client):
    case = sample_cases(client)[0]
    second = deepcopy(case)
    second["name"] = "Another name"
    second["body"] = dict(reversed(list(second["body"].items())))
    report = client.post("/api/cases/evaluate", json={"cases": [case, second]}).json()
    assert report["executed"] == 1
    assert report["duplicates"] == 1
    assert report["schema_valid_rate"] == 1


def test_response_field_assertion_failure_is_detected(client):
    case = sample_cases(client)[0]
    case["expected_fields"] = {"asset_code": "HALLUCINATED", "missing": None}
    report = client.post("/api/cases/evaluate", json={"cases": [case]}).json()
    result = report["results"][0]
    assert result["status"] == "failed"
    assert result["field_matches"] == {"asset_code": False, "missing": False}
    assert report["scenario_coverage"] == 0


def test_mislabeled_scenario_does_not_inflate_coverage(client):
    case = sample_cases(client)[0]
    case["scenario"] = "name_max"
    report = client.post("/api/cases/evaluate", json={"cases": [case]}).json()
    assert report["passed"] == 1
    assert report["results"][0]["scenario_matches"] is False
    assert report["scenario_coverage"] == 0


def test_multi_fault_input_is_not_counted_as_single_fault_coverage(client):
    case = sample_cases(client)[3]
    case["body"]["owner"] = ""
    report = client.post("/api/cases/evaluate", json={"cases": [case]}).json()
    assert report["passed"] == 1
    assert report["scenario_coverage"] == 0


@pytest.mark.parametrize("cases", [[], [None] * 51])
def test_bad_request_size(client, cases):
    assert client.post("/api/cases/evaluate", json={"cases": cases}).status_code == 422
