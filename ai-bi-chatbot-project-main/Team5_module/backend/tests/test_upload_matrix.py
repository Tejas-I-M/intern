import pytest
import pandas as pd

from conftest import register_and_login, upload_file


@pytest.mark.parametrize("fmt", ["csv", "xlsx", "json", "parquet"])
@pytest.mark.parametrize(
    "dataset_kind,expected_mode",
    [
        ("full", "full_analytics"),
        ("exploratory", "exploratory_only"),
    ],
)
def test_mixed_format_upload_matrix(client, full_mode_df, exploratory_mode_df, write_dataset, fmt, dataset_kind, expected_mode):
    register_and_login(client, email=f"matrix_{dataset_kind}_{fmt}@example.com")

    df = full_mode_df if dataset_kind == "full" else exploratory_mode_df
    file_path = write_dataset(df, fmt, f"{dataset_kind}_{fmt}")

    up = upload_file(client, file_path)
    assert up.status_code == 201
    file_id = up.get_json()["file_id"]

    analyze = client.post(f"/api/analysis/analyze/{file_id}")
    assert analyze.status_code == 200
    payload = analyze.get_json()
    assert payload["analysis_mode"] == expected_mode


def test_upload_and_analyze_include_mapping_validation(client, full_mode_df, write_dataset):
    register_and_login(client, email="mapping_validation@example.com")

    file_path = write_dataset(full_mode_df, "csv", "mapping_validation")
    up = upload_file(client, file_path)
    assert up.status_code == 201

    upload_payload = up.get_json()
    assert upload_payload["mapping_issues"] == []
    assert upload_payload["mapping_confidence"] == "HIGH"
    assert upload_payload["data_quality"]["data_quality_score"] >= 0
    assert isinstance(upload_payload["insights"], list)
    assert upload_payload["insights"]

    file_id = upload_payload["file_id"]
    analyze = client.post(f"/api/analysis/analyze/{file_id}")
    assert analyze.status_code == 200

    analyze_payload = analyze.get_json()
    assert analyze_payload["mapping_issues"] == []
    assert analyze_payload["mapping_confidence"] == "HIGH"
    assert analyze_payload["data_quality"]["data_quality_score"] >= 0
    assert isinstance(analyze_payload["insights"], list)
    assert analyze_payload["insights"]


def test_missing_values_lower_data_quality_score(client, full_mode_df, write_dataset):
    register_and_login(client, email="data_quality_missing@example.com")

    clean_path = write_dataset(full_mode_df, "csv", "quality_clean")
    clean_upload = upload_file(client, clean_path)
    assert clean_upload.status_code == 201
    clean_score = clean_upload.get_json()["data_quality"]["data_quality_score"]

    missing_df = full_mode_df.copy()
    missing_df.loc[0, "Product Category"] = None
    missing_df.loc[1, "Total Amount"] = None
    missing_path = write_dataset(missing_df, "csv", "quality_missing")
    missing_upload = upload_file(client, missing_path)
    assert missing_upload.status_code == 201
    missing_score = missing_upload.get_json()["data_quality"]["data_quality_score"]

    assert missing_score < clean_score


def test_manual_remap_flags_low_uniqueness_customer_id(client, write_dataset):
    register_and_login(client, email="mapping_bad_customer@example.com")

    bad_mapping_df = pd.DataFrame(
        {
            "order_date": [
                "2024-01-01",
                "2024-01-02",
                "2024-01-03",
                "2024-01-04",
                "2024-01-05",
                "2024-01-06",
                "2024-01-07",
                "2024-01-08",
                "2024-01-09",
                "2024-01-10",
            ],
            "sales_amount": [100, 150, 120, 180, 130, 160, 140, 170, 110, 190],
            "segment": ["Beauty", "Beauty", "Electronics", "Electronics", "Home", "Home", "Beauty", "Home", "Electronics", "Beauty"],
            "discount_bucket": ["5%", "5%", "5%", "5%", "5%", "10%", "10%", "10%", "10%", "10%"],
        }
    )

    file_path = write_dataset(bad_mapping_df, "csv", "bad_customer_mapping")
    up = upload_file(client, file_path)
    assert up.status_code == 201
    file_id = up.get_json()["file_id"]

    remap = client.post(
        f"/api/analysis/remap/{file_id}",
        json={
            "mapping": {
                "Date": "order_date",
                "Total Amount": "sales_amount",
                "Customer ID": "discount_bucket",
                "Product Category": "segment",
            }
        },
    )
    assert remap.status_code == 200

    payload = remap.get_json()
    assert payload["mapping_confidence"] == "LOW"
    assert any("Customer ID mapping is suspicious" in issue for issue in payload["mapping_issues"])
