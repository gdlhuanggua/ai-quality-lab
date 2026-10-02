from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCENARIOS = (
    "valid_create",
    "name_min",
    "name_max",
    "empty_name",
    "name_too_long",
    "invalid_code",
    "invalid_sensitivity",
    "duplicate_code",
)


class AssetInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    asset_code: str = Field(pattern=r"^[A-Z][A-Z0-9-]{2,31}$")
    name: str = Field(min_length=1, max_length=40)
    owner: str = Field(min_length=1, max_length=30)
    sensitivity: Literal["public", "internal", "confidential"]

    @field_validator("name", "owner", mode="before")
    @classmethod
    def trim_text(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value


class Asset(AssetInput):
    id: int
    created_at: str


class QualityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    records: list[dict[str, Any]] = Field(min_length=1, max_length=1000)


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cases: list[Any] = Field(min_length=1, max_length=50)


class TestCase(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(min_length=1, max_length=120)
    method: Literal["POST"]
    path: Literal["/api/assets"]
    scenario: Literal[
        "valid_create",
        "name_min",
        "name_max",
        "empty_name",
        "name_too_long",
        "invalid_code",
        "invalid_sensitivity",
        "duplicate_code",
    ]
    body: dict[str, Any]
    expected_status: Literal[201, 409, 422]
    expected_fields: dict[str, Any] = Field(default_factory=dict, max_length=10)

    @field_validator("expected_status", mode="before")
    @classmethod
    def require_integer_status(cls, value: Any) -> Any:
        if type(value) is not int:
            raise ValueError("expected_status must be an integer")
        return value
