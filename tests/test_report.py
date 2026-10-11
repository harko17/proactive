import json
import os

import pytest
from openpyxl import load_workbook

from app.config import get_metrics, get_runtime_settings
from app.newrelic_client import NewRelicDashboardClient
from app.report import ExcelReportWriter


def mock_batch_queries(monkeypatch, query_handler):
    def fake_batch(self, entries):
        response = {}
        for entry in entries:
            try:
                response[entry["alias"]] = {
                    "results": query_handler(entry["account_id"], entry["query"])
                }
            except Exception as exc:
                response[entry["alias"]] = {"error": str(exc)}
        return response

    monkeypatch.setattr(NewRelicDashboardClient, "_query_nrql_batch", fake_batch)


def test_metric_rules_only_classify_widget_types():
    rules = {rule.name: rule.metric_type for rule in get_metrics()}
    assert rules["Customer creation sync to CRM"] == "trend"
    assert rules["Shipment result processing error"] == "count"
    assert rules["Shipment instruction Cron Error"] == "count"
    assert rules["Customer creation yet to sync Sitecore/CRM"] == "latest value"
    assert rules["Shipment confirmation email"] == "trend"


def test_japan_dashboard_widget_types_match_report_specification():
    assert NewRelicDashboardClient._metric_type(
        "Order create event - Trend", "FROM Log SELECT count(*)", "viz.billboard"
    ) == "trend"
    assert NewRelicDashboardClient._metric_type(
        "Age unverified customer order count", "FROM Log SELECT count(*)", "viz.billboard"
    ) == "latest value"
    assert NewRelicDashboardClient._metric_type(
        "Sagawa Express API Error", "FROM Log SELECT count(*)", "viz.billboard"
    ) == "count"


def test_extract_from_dashboard_json_uses_nrql_results(monkeypatch):
    dashboard = {
        "pages": [
            {
                "name": "Monitoring Overview",
                "widgets": [
                    {
                        "title": "Normal Order Creation",
                        "rawConfiguration": {
                            "nrqlQueries": [{"accountId": "123", "query": "FROM Log SELECT count(*)"}]
                        },
                    }
                ],
            }
        ]
    }

    client = object.__new__(NewRelicDashboardClient)
    client.settings = {"dashboard_json": json.dumps(dashboard), "account_id": "123"}

    def fake_query(account_id, query):
        return [{"count": 42}]

    mock_batch_queries(monkeypatch, fake_query)

    rows = client.extract_from_dashboard_json()

    assert rows[0]["metric_name"] == "Normal Order Creation"
    assert rows[0]["value"] == 42
    assert rows[0]["metric_type"] == "count"
    assert rows[0]["status"] == "OK"


def test_latest_value_and_trend_choose_latest_nonzero_result_only():
    results = [
        {"count": 3, "endTimeSeconds": 1_760_000_000},
        {"count": 0, "endTimeSeconds": 1_760_000_060},
    ]

    value, timestamp = NewRelicDashboardClient._extract_latest_nonzero(results)

    assert value == 3
    assert timestamp == "2025-10-09 08:53:20 UTC"


def test_latest_value_or_trend_with_only_zero_results_is_not_zero():
    value, timestamp = NewRelicDashboardClient._extract_latest_nonzero([{"count": 0}])

    assert value is None
    assert timestamp is None


def test_timeseries_count_extracts_latest_nonzero_bucket_and_timestamp():
    results = [
        {"beginTimeSeconds": 1_791_686_399, "endTimeSeconds": 1_791_688_199, "count": 0},
        {"beginTimeSeconds": 1_791_688_199, "endTimeSeconds": 1_791_689_999, "count": 0},
        {"beginTimeSeconds": 1_791_689_999, "endTimeSeconds": 1_791_691_799, "count": 1},
        {"beginTimeSeconds": 1_791_691_799, "endTimeSeconds": 1_791_693_599, "count": 0},
    ]

    value, timestamp, status = NewRelicDashboardClient._extract_report_value(results)

    assert value == 1
    assert timestamp == "2026-10-11 04:09:59 UTC"
    assert status == "OK"


def test_count_extraction_preserves_single_aggregate_zero():
    value, timestamp, status = NewRelicDashboardClient._extract_report_value([{"count": 0}])

    assert value == 0
    assert timestamp is None
    assert status == "OK"


def test_single_timestamped_zero_bucket_remains_blank():
    result = [{"beginTimeSeconds": 1_791_686_399, "endTimeSeconds": 1_791_688_199, "count": 0}]

    assert NewRelicDashboardClient._extract_report_value(result) == (
        None,
        None,
        "No non-zero value",
    )


def test_timeseries_with_no_nonzero_counts_stays_blank():
    results = [
        {"beginTimeSeconds": 1_791_686_399, "endTimeSeconds": 1_791_688_199, "count": 0},
        {"beginTimeSeconds": 1_791_688_199, "endTimeSeconds": 1_791_689_999, "count": 0},
    ]

    assert NewRelicDashboardClient._extract_report_value(results) == (None, None, "No non-zero value")


def test_graphql_batch_result_extractor_maps_actor_alias_responses():
    response = {
        "data": {
            "actor": {
                "metric_0": {"nrql": {"results": [{"count": 312}]}},
            }
        }
    }
    entries = [{"alias": "metric_0"}]

    assert NewRelicDashboardClient._extract_graphql_batch_results(response, entries) == {
        "metric_0": {"results": [{"count": 312}]}
    }


def test_graphql_batch_result_extractor_associates_partial_errors_by_alias():
    response = {
        "data": {
            "actor": {
                "metric_0": {"nrql": {"results": [{"count": 312}]}},
            },
        },
        "errors": [{"message": "Account access denied", "path": ["actor", "metric_1", "nrql"]}],
    }
    entries = [{"alias": "metric_0"}, {"alias": "metric_1"}]

    assert NewRelicDashboardClient._extract_graphql_batch_results(response, entries) == {
        "metric_0": {"results": [{"count": 312}]},
        "metric_1": {"error": "Account access denied"},
    }


def test_graphql_batch_uses_each_entry_account_and_nrql_variable():
    entries = [
        {"account_id": "4198216", "query": "FROM Log SELECT count(*)"},
        {"account_id": "6263774", "query": "FROM Log SELECT count(*) TIMESERIES"},
    ]

    query, variables = NewRelicDashboardClient._build_graphql_batch(entries, "24 hours ago")

    assert "metric_0: account(id: 4198216)" in query
    assert "metric_1: account(id: 6263774)" in query
    assert "$nrql_0: String!" in query and "$nrql_1: String!" in query
    assert variables == {
        "nrql_0": "FROM Log SELECT count(*) SINCE 24 hours ago",
        "nrql_1": "FROM Log SELECT count(*) SINCE 24 hours ago TIMESERIES",
    }
    assert entries[0]["alias"] == "metric_0"
    assert entries[1]["alias"] == "metric_1"


def test_graphql_http_request_uses_postman_headers_and_variable_payload(monkeypatch):
    client = object.__new__(NewRelicDashboardClient)
    client.settings = {
        "api_key": "test-api-key",
        "graphql_endpoint": "https://api.newrelic.com/graphql",
        "reporting_window": "24 hours ago",
    }
    entries = [{
        "account_id": "4198216",
        "query": "FROM Log SELECT count(*)",
        "alias": "metric_0",
    }]
    captured = {}

    class MockResponse:
        status_code = 200
        headers = {}
        text = ""

        @staticmethod
        def json():
            return {"data": {"actor": {"metric_0": {"nrql": {"results": [{"count": 5}]}}}}}

    def fake_post(url, headers, json, timeout):
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        return MockResponse()

    monkeypatch.setattr("app.newrelic_client.requests.post", fake_post)
    result = client._query_nrql_batch(entries)

    assert captured["url"] == "https://api.newrelic.com/graphql"
    assert captured["headers"] == {
        "API-Key": "test-api-key",
        "Content-Type": "application/json",
    }
    assert captured["json"]["variables"] == {
        "nrql_0": "FROM Log SELECT count(*) SINCE 24 hours ago"
    }
    assert "metric_0: account(id: 4198216)" in captured["json"]["query"]
    assert result == {"metric_0": {"results": [{"count": 5}]}}


def test_dashboard_batch_maps_each_result_to_its_query_account(monkeypatch):
    dashboard = {
        "pages": [{
            "name": "Monitoring",
            "widgets": [
                {
                    "title": "Account A",
                    "rawConfiguration": {"nrqlQueries": [{
                        "accountId": "4198216",
                        "query": "FROM Log SELECT count(*)",
                    }]},
                },
                {
                    "title": "Account B",
                    "rawConfiguration": {"nrqlQueries": [{
                        "accountId": "6263774",
                        "query": "FROM Log SELECT uniqueCount(message)",
                    }]},
                },
            ],
        }],
    }
    client = object.__new__(NewRelicDashboardClient)
    client.settings = {"dashboard_json": json.dumps(dashboard)}
    sent = []

    def fake_batch(self, entries):
        sent.extend((entry["account_id"], entry["query"]) for entry in entries)
        return {
            entries[0]["alias"]: {"results": [{"count": 11}]},
            entries[1]["alias"]: {"results": [{"uniqueCount": 22}]},
        }

    monkeypatch.setattr(NewRelicDashboardClient, "_query_nrql_batch", fake_batch)
    rows = client.extract_from_dashboard_json()

    assert sent == [
        ("4198216", "FROM Log SELECT count(*)"),
        ("6263774", "FROM Log SELECT uniqueCount(message)"),
    ]
    assert [(row["account_id"], row["value"]) for row in rows] == [
        ("4198216", 11),
        ("6263774", 22),
    ]


def test_metric_type_inference_preserves_config_and_detects_trends():
    assert NewRelicDashboardClient._metric_type(
        "Pending / Processing status",
        "FROM Log SELECT count(*) TIMESERIES",
        "viz.line",
    ) == "latest value"
    assert NewRelicDashboardClient._metric_type(
        "A new dashboard metric",
        "FROM Log SELECT count(*) TIMESERIES",
        "viz.line",
    ) == "trend"
    assert NewRelicDashboardClient._metric_type(
        "A new dashboard metric",
        "FROM Log SELECT count(*)",
        "viz.billboard",
    ) == "count"


def test_dashboard_report_selects_latest_nonzero_for_latest_value_and_trend(monkeypatch):
    dashboard = {
        "name": "Test Dashboard",
        "pages": [{
            "name": "Monitoring",
            "widgets": [
                {
                    "title": "",
                    "visualization": {"id": "viz.markdown"},
                    "rawConfiguration": {"text": "# Monitoring\n## Order Creation"},
                },
                {
                    "title": "Pending / Processing status",
                    "visualization": {"id": "viz.line"},
                    "rawConfiguration": {"nrqlQueries": [{
                        "accountId": "123",
                        "query": "FROM Log SELECT count(*) TIMESERIES",
                    }]},
                },
                {
                    "title": "Recently added metric",
                    "visualization": {"id": "viz.line"},
                    "rawConfiguration": {"nrqlQueries": [{
                        "accountId": "456",
                        "query": "FROM Log SELECT count(*) TIMESERIES",
                    }]},
                },
            ],
        }],
    }
    client = object.__new__(NewRelicDashboardClient)
    client.settings = {"dashboard_json": json.dumps(dashboard)}

    def fake_query(account_id, query):
        return [
            {"count": 8, "endTimeSeconds": 1_760_000_000},
            {"count": 0, "endTimeSeconds": 1_760_000_060},
        ]

    mock_batch_queries(monkeypatch, fake_query)
    rows = client.extract_from_dashboard_json()

    assert [(row["metric_type"], row["value"], row["timestamp"]) for row in rows] == [
        ("latest value", 8, "2025-10-09 08:53:20 UTC"),
        ("trend", 8, "2025-10-09 08:53:20 UTC"),
    ]
    assert all(row["category"] == "Monitoring / Order Creation" for row in rows)


def test_dashboard_count_widget_uses_latest_nonzero_timeseries_count(monkeypatch, tmp_path):
    dashboard = {
        "name": "Japan Monitoring",
        "pages": [{
            "name": "Monitoring",
            "widgets": [{
                "title": "Order confirmation email",
                "visualization": {"id": "viz.billboard"},
                "rawConfiguration": {"nrqlQueries": [{
                    "accountId": "4198216",
                    "query": "FROM Log SELECT count(*) SINCE 24 HOURS AGO TIMESERIES",
                }]},
            }],
        }],
    }
    client = object.__new__(NewRelicDashboardClient)
    client.settings = {"dashboard_json": json.dumps(dashboard)}

    def fake_query(account_id, query):
        assert account_id == "4198216"
        return [
            {"beginTimeSeconds": 1_791_686_399, "endTimeSeconds": 1_791_688_199, "count": 0},
            {"beginTimeSeconds": 1_791_688_199, "endTimeSeconds": 1_791_689_999, "count": 0},
            {"beginTimeSeconds": 1_791_689_999, "endTimeSeconds": 1_791_691_799, "count": 1},
            {"beginTimeSeconds": 1_791_691_799, "endTimeSeconds": 1_791_693_599, "count": 0},
        ]

    mock_batch_queries(monkeypatch, fake_query)
    rows = client.extract_from_dashboard_json()

    assert rows[0]["metric_type"] == "trend"
    assert rows[0]["value"] == 1
    assert rows[0]["timestamp"] == "2026-10-11 04:09:59 UTC"
    assert rows[0]["status"] == "OK"

    report_path = tmp_path / "japan-report.xlsx"
    ExcelReportWriter(str(report_path)).write(rows)
    sheet = load_workbook(report_path, data_only=True)["Dashboard Summary"]
    assert sheet["D2"].value == 1


def test_dashboard_json_keeps_rows_when_query_fails_or_returns_no_value(monkeypatch):
    dashboard = {
        "name": "Production Dashboard",
        "pages": [{
            "name": "Overview",
            "widgets": [
                {
                    "title": "Query failed",
                    "visualization": {"id": "viz.billboard"},
                    "rawConfiguration": {"nrqlQueries": [{
                        "accountId": "101",
                        "query": "FROM Log SELECT count(*)",
                    }]},
                },
                {
                    "title": "No matching data",
                    "visualization": {"id": "viz.billboard"},
                    "rawConfiguration": {"nrqlQueries": [{
                        "accountId": "102",
                        "query": "FROM Log SELECT count(*)",
                    }]},
                },
                {
                    "title": "Missing account",
                    "visualization": {"id": "viz.billboard"},
                    "rawConfiguration": {"nrqlQueries": [{
                        "query": "FROM Log SELECT count(*)",
                    }]},
                },
                {
                    "title": "Missing query config",
                    "visualization": {"id": "viz.billboard"},
                    "rawConfiguration": {},
                },
            ],
        }],
    }
    client = object.__new__(NewRelicDashboardClient)
    client.settings = {"dashboard_json": json.dumps(dashboard)}

    def fake_query(account_id, query):
        if account_id == "101":
            raise RuntimeError("mock API failure")
        return []

    mock_batch_queries(monkeypatch, fake_query)
    with pytest.warns(UserWarning):
        rows = client.extract_from_dashboard_json()

    assert [row["metric_name"] for row in rows] == [
        "Query failed",
        "No matching data",
        "Missing account",
        "Missing query config",
    ]
    assert [row["value"] for row in rows] == [None, None, None, None]
    assert [row["status"] for row in rows] == [
        "Query failed",
        "No numeric result",
        "No account ID",
        "No NRQL query",
    ]
    assert all(row["dashboard_name"] == "Production Dashboard" for row in rows)


def test_extract_from_dashboard_json_accepts_long_json_string(monkeypatch):
    dashboard = {
        "name": "New Proactive Business Monitoring - ZA count",
        "pages": [
            {
                "name": "Monitoring Overview",
                "widgets": [
                    {
                        "title": "Pending Payment Cancellations",
                        "rawConfiguration": {"nrqlQueries": [{"accountId": "123", "query": "FROM Log SELECT count(*)"}]},
                    }
                ],
            }
        ],
        "notes": "\n".join(["# Proactive Business Monitoring Dashboard for ZA"] * 80),
    }
    dashboard_json = json.dumps(dashboard)

    client = object.__new__(NewRelicDashboardClient)
    client.settings = {"dashboard_json": dashboard_json, "account_id": "123"}

    def fake_query(account_id, query):
        return [{"count": 7}]

    mock_batch_queries(monkeypatch, fake_query)

    rows = client.extract_from_dashboard_json()

    assert rows[0]["metric_name"] == "Pending Payment Cancellations"
    assert rows[0]["value"] == 7


def test_extract_from_dashboard_json_includes_all_widgets_with_queries(monkeypatch):
    dashboard = {
        "name": "New Proactive Business Monitoring -  ZA  count",
        "pages": [
            {
                "name": "Monitoring Overview",
                "widgets": [
                    {"title": "Normal Order Creation", "rawConfiguration": {"nrqlQueries": [{"accountId": "123", "query": "FROM Log SELECT count(*)"}]}}
                    ,
                    {"title": "Pending Payment Cancellations", "rawConfiguration": {"nrqlQueries": [{"accountId": "123", "query": "FROM Log SELECT count(*)"}]}}
                    ,
                    {"title": "Order fulfilment Request - Failures", "rawConfiguration": {"nrqlQueries": [{"accountId": "123", "query": "FROM Log SELECT count(*)"}]}}
                    ,
                    {"title": "Order fulfilment Request - Failures to read response", "rawConfiguration": {"nrqlQueries": [{"accountId": "123", "query": "FROM Log SELECT count(*)"}]}}
                    ,
                    {"title": "Shipment creation", "rawConfiguration": {"nrqlQueries": [{"accountId": "123", "query": "FROM Log SELECT count(*)"}]}}
                    ,
                    {"title": "Customer Sync to Magento - Error", "rawConfiguration": {"nrqlQueries": [{"accountId": "123", "query": "FROM Log SELECT count(*)"}]}}
                    ,
                    {"title": "Contact Form - Error", "rawConfiguration": {"nrqlQueries": [{"accountId": "123", "query": "FROM Log SELECT count(*)"}]}}
                    ,
                    {"title": "Inventory Sync error", "rawConfiguration": {"nrqlQueries": [{"accountId": "123", "query": "FROM Log SELECT count(*)"}]}}
                    ,
                    {"title": "Account confirmation email", "rawConfiguration": {"nrqlQueries": [{"accountId": "123", "query": "FROM Log SELECT count(*)"}]}}
                ],
            }
        ],
    }

    client = object.__new__(NewRelicDashboardClient)
    client.settings = {"dashboard_json": json.dumps(dashboard), "account_id": "123"}

    def fake_query(account_id, query):
        return [{"count": 1}]

    mock_batch_queries(monkeypatch, fake_query)

    rows = client.extract_from_dashboard_json()
    metric_names = [row["metric_name"] for row in rows]

    assert "Normal Order Creation" in metric_names
    assert "Account confirmation email" in metric_names
    assert "Pending Payment Cancellations" in metric_names
    assert "Order fulfilment Request - Failures" in metric_names
    assert "Order fulfilment Request - Failures to read response" in metric_names
    assert "Shipment creation" in metric_names
    assert "Customer Sync to Magento - Error" in metric_names
    assert "Contact Form - Error" in metric_names
    assert "Inventory Sync error" in metric_names


def test_excel_report_writer_creates_parent_directory(tmp_path):
    target = tmp_path / "nested" / "report.xlsx"

    writer = ExcelReportWriter(str(target))
    saved_path = writer.write([
        {
            "timestamp": "now",
            "dashboard_url": "https://one.newrelic.com/dashboards",
            "category": "Order Creation",
            "metric_name": "Test metric",
            "metric_type": "count",
            "value": "42",
            "unit": "items",
            "source": "unit test",
        },
        {
            "category": "Order Creation",
            "metric_name": "Test latest metric",
            "metric_type": "latest value",
            "value": 9,
        },
    ])

    assert saved_path == str(target)
    assert target.exists()
    workbook = load_workbook(target)
    sheet = workbook["Dashboard Summary"]
    assert sheet["A1"].value == "New Relic Dashboard - Monitoring charts"
    assert sheet["C1"].value == "Monitoring"
    assert sheet["D2"].value == 42
    assert sheet["C2"].value == "count"
    assert sheet["A1"].hyperlink.target == "https://one.newrelic.com/dashboards"
    assert "A2:A3" in {str(merged_range) for merged_range in sheet.merged_cells.ranges}
    assert sheet["A2"].alignment.horizontal == "center"


def test_extract_from_real_dashboard_json_preserves_query_account_and_category(monkeypatch):
    dashboard_path = os.path.join(os.path.dirname(__file__), "..", "dashboard.json")
    client = object.__new__(NewRelicDashboardClient)
    client.settings = {"dashboard_json": dashboard_path, "account_id": ""}
    calls = []

    def fake_query(account_id, query):
        calls.append((account_id, query))
        return [{"count": 2}]

    mock_batch_queries(monkeypatch, fake_query)
    rows = client.extract_from_dashboard_json()

    assert len(rows) == len(calls) == 20
    assert all(account_id == "6538703" for account_id, _ in calls)
    assert all(row["account_id"] == "6538703" for row in rows)
    assert rows[0]["category"] == "Order Creation"


def test_real_dashboard_export_keeps_all_rows_when_api_queries_fail(monkeypatch, tmp_path):
    dashboard_path = os.path.join(os.path.dirname(__file__), "..", "dashboard.json")
    client = object.__new__(NewRelicDashboardClient)
    client.settings = {"dashboard_json": dashboard_path, "account_id": ""}

    def failed_query(account_id, query):
        raise RuntimeError("simulated API failure")

    mock_batch_queries(monkeypatch, failed_query)
    with pytest.warns(UserWarning):
        rows = client.extract_from_dashboard_json()

    assert len(rows) == 20
    assert all(row["value"] is None for row in rows)
    assert all(row["status"] == "Query failed" for row in rows)

    output = tmp_path / "report.xlsx"
    ExcelReportWriter(str(output)).write(rows)
    sheet = load_workbook(output, data_only=True)["Dashboard Summary"]
    assert sheet.max_row == 21
    assert sheet["A1"].value.startswith("New Proactive Business Monitoring")
    assert sheet["B2"].value == "Normal Order Creation"
    assert sheet["D2"].value is None
    assert sheet["B21"].value
    assert sheet["D21"].value is None


def test_run_fails_loudly_after_saving_report_when_api_queries_fail(monkeypatch, tmp_path):
    client = object.__new__(NewRelicDashboardClient)
    client.settings = {
        "dashboard_json": json.dumps({
            "pages": [{
                "name": "Overview",
                "widgets": [{
                    "title": "Unavailable",
                    "rawConfiguration": {"nrqlQueries": [{
                        "accountId": "101",
                        "query": "FROM Log SELECT count(*)",
                    }]},
                }],
            }],
        }),
        "output_path": str(tmp_path / "report.xlsx"),
    }
    def failed_query(account_id, query):
        raise RuntimeError("API unavailable")

    mock_batch_queries(monkeypatch, failed_query)

    with pytest.warns(UserWarning), pytest.raises(RuntimeError, match="could not be queried successfully"):
        client.run()
    assert (tmp_path / "report.xlsx").exists()


def test_get_runtime_settings_requires_only_api_key(monkeypatch):
    monkeypatch.delenv("NEW_RELIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="Missing required environment variable"):
        get_runtime_settings()

    monkeypatch.setenv("NEW_RELIC_API_KEY", "test-key")
    settings = get_runtime_settings()
    assert settings["api_key"] == "test-key"
    assert settings["dashboard_json"].endswith("dashboard.json")
