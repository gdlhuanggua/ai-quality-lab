import json
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.models import AssetInput, SCENARIOS, TestCase
from app.quality import error_details

DUPLICATE_FIXTURE = {
    "asset_code": "DUP-001",
    "name": "Existing fixture",
    "owner": "demo-team",
    "sensitivity": "internal",
}


def matches_scenario(case: TestCase) -> bool:
    # Coverage only counts single-fault inputs matching the fixed scenario contract.
    try:
        validated = AssetInput.model_validate(case.body)
    except ValidationError as error:
        errors = error.errors()
        if len(errors) != 1:
            return False
        field, kind = errors[0]["loc"], errors[0]["type"]
        return {
            "empty_name": field == ("name",) and kind == "string_too_short",
            "name_too_long": field == ("name",) and kind == "string_too_long",
            "invalid_code": field == ("asset_code",) and kind == "string_pattern_mismatch",
            "invalid_sensitivity": field == ("sensitivity",) and kind == "literal_error",
        }.get(case.scenario, False)
    if case.scenario == "duplicate_code":
        return validated.asset_code == DUPLICATE_FIXTURE["asset_code"]
    if case.scenario == "name_min":
        return len(validated.name) == 1
    if case.scenario == "name_max":
        return len(validated.name) == 40
    return case.scenario == "valid_create"


def evaluate_cases(cases: list) -> dict:
    from app.main import create_app

    results, seen, covered = [], set(), set()
    accepted = passed = duplicates = 0
    for index, raw in enumerate(cases, start=1):
        result = {
            "index": index,
            "name": raw.get("name", f"Case {index}") if isinstance(raw, dict) else f"Case {index}",
            "status": "rejected",
        }
        try:
            case = TestCase.model_validate(raw)
        except ValidationError as error:
            result["issues"] = error_details(error)
            results.append(result)
            continue
        signature = json.dumps(
            {
                "method": case.method,
                "path": case.path,
                "body": case.body,
                "duplicate_fixture": case.scenario == "duplicate_code",
            },
            sort_keys=True,
            ensure_ascii=True,
        )
        if signature in seen:
            duplicates += 1
            result["status"] = "duplicate"
            result["issues"] = [{"field": "body", "message": "Duplicate request; skipped"}]
            results.append(result)
            continue
        seen.add(signature)
        accepted += 1
        # Each case has its own database; even identical codes cannot leak state.
        with TemporaryDirectory(prefix="quality-lab-") as directory:
            with TestClient(create_app(Path(directory) / "cases.db", tools=False)) as client:
                if case.scenario == "duplicate_code":
                    fixture = client.post("/api/assets", json=DUPLICATE_FIXTURE)
                    if fixture.status_code != 201:
                        raise RuntimeError("Could not create the duplicate-code fixture")
                response = client.post(case.path, json=case.body)
                actual = response.json()
        field_matches = {
            key: isinstance(actual, dict) and key in actual and actual[key] == value
            for key, value in case.expected_fields.items()
        }
        assertions_pass = response.status_code == case.expected_status and all(field_matches.values())
        scenario_matches = matches_scenario(case)
        passed += int(assertions_pass)
        if assertions_pass and scenario_matches:
            covered.add(case.scenario)
        result.update(
            status="passed" if assertions_pass else "failed",
            scenario=case.scenario,
            scenario_matches=scenario_matches,
            expected_status=case.expected_status,
            actual_status=response.status_code,
            field_matches=field_matches,
            actual=actual,
        )
        results.append(result)
    total = len(cases)
    return {
        "total": total,
        "schema_valid": accepted + duplicates,
        "schema_valid_rate": round((accepted + duplicates) / total, 4),
        "duplicates": duplicates,
        "executed": accepted,
        "passed": passed,
        "failed": accepted - passed,
        "assertion_pass_rate": round(passed / accepted, 4) if accepted else None,
        "covered_scenarios": [scenario for scenario in SCENARIOS if scenario in covered],
        "uncovered_scenarios": [scenario for scenario in SCENARIOS if scenario not in covered],
        "scenario_coverage": round(len(covered) / len(SCENARIOS), 4),
        "scenario_total": len(SCENARIOS),
        "results": results,
    }
