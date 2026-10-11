import json
import re
from pathlib import Path

import pytest
from openpyxl import load_workbook

from app.config import get_metrics, get_runtime_settings
from app.newrelic_client import NewRelicDashboardClient
from app.report import ExcelReportWriter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CURL_FILE = PROJECT_ROOT / "CURLS.md"


def build_mock_response(entries):
    values = {
        "normalOrderCreation": 246,
        "shipmentInstructionCronMonitor": 15,
        "docomoOutboundApiCall": 43,
        "ordersYetToSyncDownstream": 62,
    }
    actor = {}
    for entry in entries:
        query = entry["query"]
        if "TIMESERIES" in query.upper():
            match = re.search(
                r"(uniqueCount|count)\s*\(\s*`?(message|\*)`?\s*\)",
                query,
                re.IGNORECASE,
            )
            if match:
                aggregate = "uniqueCount" if match.group(1).lower() == "uniquecount" else "count"
                key = f"{aggregate}.{match.group(2)}" if match.group(2) != "*" else aggregate
            else:
                key = "count"
            value = values.get(entry["alias"], 0)
            results = [
                {"beginTimeSeconds": 1_791_686_399, "endTimeSeconds": 1_791_688_199, key: 0},
                {"beginTimeSeconds": 1_791_688_199, "endTimeSeconds": 1_791_689_999, key: value},
                {"beginTimeSeconds": 1_791_689_999, "endTimeSeconds": 1_791_691_799, key: 0},
            ]
        else:
            results = [{"count": values.get(entry["alias"], 0)}]
        actor[entry["alias"]] = {"nrql": {"results": results}}
    return {"data": {"actor": actor}}


def make_client(**settings):
    client = object.__new__(NewRelicDashboardClient)
    client.settings = {
        "curl_file": str(CURL_FILE),
        "api_key": "test-api-key",
        "graphql_endpoint": "https://api.newrelic.com/graphql",
        "reporting_window": "24 hours ago",
        "output_path": str(PROJECT_ROOT / "output" / "test-report.xlsx"),
        **settings,
    }
    return client


def test_curl_request_defines_all_japan_queries_and_their_accounts():
    client = make_client()
    payload, entries = client._load_curl_request()

    assert len(entries) == len(get_metrics()) == 34
    assert payload["query"].startswith("query DashboardMetrics")
    assert {entry["account_id"] for entry in entries} == {"4198216", "6263774"}
    assert all(entry["query"].startswith(("FROM Log", "SELECT")) for entry in entries)

    pricebook = next(entry for entry in entries if entry["alias"] == "productUpdatePricebookError")
    crm_sync = next(entry for entry in entries if entry["alias"] == "customerCreationYetToSyncSitecoreCrm")
    assert pricebook["account_id"] == "6263774"
    assert crm_sync["account_id"] == "6263774"
    assert "%JP-order-count%" in entries[0]["query"]
    assert len({entry["alias"] for entry in entries}) == 34


def test_latest_nonzero_time_series_bucket_wins_even_if_last_is_zero():
    buckets = [
        {"beginTimeSeconds": 1_791_686_399, "endTimeSeconds": 1_791_688_199, "count": 0},
        {"beginTimeSeconds": 1_791_688_199, "endTimeSeconds": 1_791_689_999, "count": 0},
        {"beginTimeSeconds": 1_791_689_999, "endTimeSeconds": 1_791_691_799, "count": 1},
        {"beginTimeSeconds": 1_791_691_799, "endTimeSeconds": 1_791_693_599, "count": 0},
    ]

    value, timestamp, status = NewRelicDashboardClient._extract_report_value(buckets)

    assert value == 1
    assert timestamp == "2026-10-11 04:09:59 UTC"
    assert status == "OK"


def test_count_message_time_series_uses_metric_not_timestamp():
    buckets = [
        {"beginTimeSeconds": 1_791_686_399, "endTimeSeconds": 1_791_688_199, "count.message": 0},
        {"beginTimeSeconds": 1_791_688_199, "endTimeSeconds": 1_791_689_999, "count.message": 2},
        {"beginTimeSeconds": 1_791_689_999, "endTimeSeconds": 1_791_691_799, "count.message": 0},
    ]

    assert NewRelicDashboardClient._extract_report_value(buckets) == (
        2,
        "2026-10-11 03:39:59 UTC",
        "OK",
    )


def test_unique_count_message_time_series_uses_latest_nonzero_count():
    buckets = [
        {"beginTimeSeconds": 1_791_686_399, "endTimeSeconds": 1_791_688_199, "uniqueCount.message": 3},
        {"beginTimeSeconds": 1_791_688_199, "endTimeSeconds": 1_791_689_999, "uniqueCount.message": 0},
    ]

    assert NewRelicDashboardClient._extract_report_value(buckets) == (
        3,
        "2026-10-11 03:09:59 UTC",
        "OK",
    )


def test_single_aggregate_count_zero_is_preserved():
    assert NewRelicDashboardClient._extract_report_value([{"count": 0}]) == (
        0,
        None,
        "OK",
    )


def test_all_zero_time_series_is_blank_not_zero():
    buckets = [
        {"beginTimeSeconds": 1_791_686_399, "endTimeSeconds": 1_791_688_199, "count": 0},
        {"beginTimeSeconds": 1_791_688_199, "endTimeSeconds": 1_791_689_999, "count": 0},
    ]

    assert NewRelicDashboardClient._extract_report_value(buckets) == (
        None,
        None,
        "No non-zero value",
    )


def test_graphql_alias_errors_do_not_discard_successful_results():
    entries = [{"alias": "good"}, {"alias": "bad"}]
    response = {
        "data": {"actor": {"good": {"nrql": {"results": [{"count": 4}]}}}},
        "errors": [{"message": "Account access denied", "path": ["actor", "bad", "nrql"]}],
    }

    assert NewRelicDashboardClient._extract_graphql_batch_results(response, entries) == {
        "good": {"results": [{"count": 4}]},
        "bad": {"error": "Account access denied"},
    }


def test_graphql_response_maps_every_alias_into_report_rows():
    client = make_client()
    _, entries = client._load_curl_request()
    response = build_mock_response(entries)
    rows = client._rows_from_graphql_response(response, entries)
    by_alias = {entry["alias"]: row for entry, row in zip(entries, rows)}

    assert len(rows) == 34
    assert by_alias["normalOrderCreation"]["value"] == 246
    assert by_alias["shipmentInstructionCronMonitor"]["value"] == 15
    assert by_alias["docomoOutboundApiCall"]["value"] == 43
    assert by_alias["ordersYetToSyncDownstream"]["value"] == 62
    assert by_alias["deviceTrialPaymentPendingCharge"]["value"] is None
    assert by_alias["deviceTrialPaymentPendingCharge"]["status"] == "No non-zero value"
    assert by_alias["normalOrderCreation"]["account_id"] == "4198216"
    assert by_alias["productUpdatePricebookError"]["account_id"] == "6263774"


def test_report_writes_api_counts_and_keeps_all_rows(tmp_path):
    client = make_client(output_path=str(tmp_path / "japan-report.xlsx"))
    _, entries = client._load_curl_request()
    response = build_mock_response(entries)
    rows = client._rows_from_graphql_response(response, entries)

    saved_path = ExcelReportWriter(client.settings["output_path"]).write(rows)
    sheet = load_workbook(saved_path, data_only=True)["Dashboard Summary"]

    assert sheet.max_row == 35
    assert sheet["A1"].value == "Japan - Monitoring charts"
    assert sheet["B2"].value == "Normal Order Creation"
    assert sheet["D2"].value == 246
    assert sheet["D7"].value == 15
    assert "A2:A6" in {str(item) for item in sheet.merged_cells.ranges}


def test_api_post_sends_exact_curl_body_and_postman_headers(monkeypatch):
    client = make_client()
    payload, entries = client._load_curl_request()
    captured = {}

    class MockResponse:
        status_code = 200
        headers = {}
        text = ""

        @staticmethod
        def json():
            return build_mock_response(entries)

    def fake_post(url, headers, json, timeout):
        captured.update(url=url, headers=headers, payload=json, timeout=timeout)
        return MockResponse()

    monkeypatch.setattr("app.newrelic_client.requests.post", fake_post)
    response = client._send_graphql_payload(payload, entries)

    assert response["data"]["actor"]["normalOrderCreation"]["nrql"]["results"][0]["count"] == 246
    assert captured["url"] == "https://api.newrelic.com/graphql"
    assert captured["headers"] == {
        "API-Key": "test-api-key",
        "Content-Type": "application/json",
    }
    assert captured["payload"] == payload
    assert "variables" not in captured["payload"]


def test_run_builds_japan_workbook_from_mocked_live_api_response(monkeypatch, tmp_path):
    output_path = tmp_path / "report.xlsx"
    client = make_client(output_path=str(output_path))
    _, entries = client._load_curl_request()
    response = build_mock_response(entries)
    monkeypatch.setattr(
        NewRelicDashboardClient,
        "_send_graphql_payload",
        lambda self, payload, entries: response,
    )

    assert client.run() == str(output_path)
    sheet = load_workbook(output_path, data_only=True)["Dashboard Summary"]
    assert sheet.max_row == 35
    assert sheet["B2"].value == "Normal Order Creation"
    assert sheet["D2"].value == 246
    assert sheet["B35"].value == "Age unverified customer order count"
    assert sheet["D35"].value in (None, 0)


def test_runtime_settings_require_only_api_key(monkeypatch):
    monkeypatch.delenv("NEW_RELIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="NEW_RELIC_API_KEY"):
        get_runtime_settings()

    monkeypatch.setenv("NEW_RELIC_API_KEY", "test-key")
    settings = get_runtime_settings()

    assert settings["api_key"] == "test-key"
    assert settings["curl_file"].endswith("CURLS.md")
