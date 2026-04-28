import json
from pathlib import Path

from conftest import register_and_login, upload_file


SNAPSHOT_PATH = Path(__file__).parent / "snapshots" / "api_contract_snapshot.json"


def _keys(d):
    return sorted(list(d.keys())) if isinstance(d, dict) else []


def test_api_contract_snapshot_stability(client, full_mode_df, write_dataset):
    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))

    register_and_login(client, email="snapshot@example.com")

    health = client.get("/api/health")
    health_body = health.get_json() or {}

    csv_path = write_dataset(full_mode_df, "csv", "snapshot_full")
    up = upload_file(client, csv_path)
    assert up.status_code == 201
    up_body = up.get_json() or {}
    file_id = up_body["file_id"]

    analyze = client.post(f"/api/analysis/analyze/{file_id}")
    assert analyze.status_code == 200
    analyze_body = analyze.get_json() or {}

    chat = client.post(
        f"/api/analysis/chat/{file_id}",
        json={"question": "What is my revenue trend this month?", "use_gemini": False},
    )
    assert chat.status_code == 200
    chat_body = chat.get_json() or {}

    async_submit = client.post(f"/api/analysis/analyze-async/{file_id}", json={})
    assert async_submit.status_code == 202
    async_body = async_submit.get_json() or {}

    job = client.get(f"/api/analysis/jobs/{async_body['job_id']}")
    assert job.status_code == 200
    job_body = job.get_json() or {}

    observed = {
        "health": {"keys": _keys(health_body)},
        "upload": {"keys": _keys(up_body)},
        "analyze": {
            "keys": _keys(analyze_body),
            "results_keys": _keys(analyze_body.get("results", {})),
            "business_snapshot_keys": _keys((analyze_body.get("results", {}) or {}).get("business_snapshot", {})),
        },
        "chat": {"keys": _keys(chat_body)},
        "analyze_async": {"keys": _keys(async_body)},
        "job_status": {
            "keys": _keys(job_body),
            "job_keys": _keys(job_body.get("job", {})),
        },
    }

    for endpoint, spec in expected.items():
        for key_name, required_keys in spec.items():
            assert set(required_keys).issubset(set(observed[endpoint][key_name])), (
                f"Contract mismatch on {endpoint}.{key_name}: "
                f"missing {set(required_keys) - set(observed[endpoint][key_name])}"
            )
