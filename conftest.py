import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "test.db")) as test_client:
        yield test_client


@pytest.fixture
def asset_body():
    return {
        "asset_code": "DATA-001",
        "name": "Demo asset",
        "owner": "demo-team",
        "sensitivity": "internal",
    }
