from collections import Counter

from pydantic import ValidationError

from app.models import AssetInput


def error_details(error: ValidationError) -> list[dict]:
    return [
        {"field": ".".join(map(str, item["loc"])), "message": item["msg"]}
        for item in error.errors(include_url=False, include_context=False, include_input=False)
    ]


def inspect_quality(records: list[dict]) -> dict:
    codes = Counter(
        record["asset_code"]
        for record in records
        if isinstance(record.get("asset_code"), str)
    )
    rows = []
    for index, record in enumerate(records, start=1):
        issues = []
        try:
            AssetInput.model_validate(record)
        except ValidationError as error:
            issues.extend(error_details(error))
        code = record.get("asset_code")
        if isinstance(code, str) and codes[code] > 1:
            issues.append({"field": "asset_code", "message": "Duplicate asset_code"})
        rows.append({"row": index, "valid": not issues, "issues": issues})
    valid = sum(row["valid"] for row in rows)
    return {
        "total": len(rows),
        "valid": valid,
        "invalid": len(rows) - valid,
        "valid_rate": round(valid / len(rows), 4),
        "rows": rows,
    }
