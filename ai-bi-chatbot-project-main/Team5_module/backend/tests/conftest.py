import io
import os
import sys
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if "auth" in sys.modules and not hasattr(sys.modules["auth"], "__path__"):
    del sys.modules["auth"]

auth_init = BACKEND_DIR / "auth" / "__init__.py"
spec = importlib.util.spec_from_file_location(
    "auth",
    auth_init,
    submodule_search_locations=[str(BACKEND_DIR / "auth")],
)
auth_module = importlib.util.module_from_spec(spec)
sys.modules["auth"] = auth_module
assert spec.loader is not None
spec.loader.exec_module(auth_module)

from app import create_app
from api import analysis_routes
from auth import auth_handler


def _full_mode_df():
    return pd.DataFrame(
        {
            "Customer ID": ["C1", "C2", "C3", "C1", "C4", "C5"],
            "Date": [
                "2024-01-01",
                "2024-01-08",
                "2024-01-15",
                "2024-01-22",
                "2024-01-29",
                "2024-02-05",
            ],
            "Total Amount": [120.0, 320.0, 80.0, 450.0, 210.0, 95.0],
            "Product Category": ["Beauty", "Electronics", "Grocery", "Electronics", "Beauty", "Home"],
        }
    )


def _exploratory_mode_df():
    return pd.DataFrame(
        {
            "employee_name": ["A", "B", "C", "D"],
            "department": ["IT", "HR", "IT", "Finance"],
            "salary": [50000, 62000, 58000, 71000],
            "join_date": ["2022-01-01", "2021-06-01", "2023-03-15", "2020-11-10"],
        }
    )


@pytest.fixture
def app(tmp_path, monkeypatch):
    users_db = tmp_path / "users.json"
    recent_path = tmp_path / "recent_analyses.json"

    monkeypatch.setattr(auth_handler, "USER_DATABASE_FILE", str(users_db))
    monkeypatch.setattr(analysis_routes, "RECENT_ANALYSIS_FILE", str(recent_path))

    analysis_routes.user_datasets.clear()
    analysis_routes.user_analyses.clear()
    analysis_routes.chat_histories.clear()
    analysis_routes.analysis_jobs.clear()

    application = create_app("development")
    application.config.update(TESTING=True)
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def full_mode_df():
    return _full_mode_df()


@pytest.fixture
def exploratory_mode_df():
    return _exploratory_mode_df()


def _write_df(df: pd.DataFrame, fmt: str, path: Path):
    if fmt == "csv":
        df.to_csv(path, index=False)
    elif fmt == "xlsx":
        df.to_excel(path, index=False)
    elif fmt == "json":
        df.to_json(path, orient="records")
    elif fmt == "parquet":
        df.to_parquet(path, index=False)
    else:
        raise ValueError(f"Unsupported format: {fmt}")


@pytest.fixture
def write_dataset(tmp_path):
    def _writer(df: pd.DataFrame, fmt: str, name: str):
        path = tmp_path / f"{name}.{fmt}"
        _write_df(df, fmt, path)
        return path

    return _writer


def register_and_login(client, email="qa@example.com", password="12345678"):
    client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "firstName": "QA",
            "lastName": "User",
            "password": password,
        },
    )
    login = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200


def upload_file(client, file_path: Path, dataset_name=None):
    dataset_name = dataset_name or file_path.name
    with open(file_path, "rb") as f:
        response = client.post(
            "/api/analysis/upload",
            data={"dataset_name": dataset_name, "file": (f, file_path.name)},
            content_type="multipart/form-data",
        )
    return response
