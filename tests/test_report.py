import json
import os
import re

import pytest
from openpyxl import load_workbook

from app.config import get_metrics, get_runtime_settings
from app.newrelic_client import NewRelicDashboardClient
from app.report import ExcelReportWriter, build_rows


def test_build_rows_extracts_and_normalizes_values():
    page_text = """
    Normal Order Creation 12,450
    Pending / Processing status 3.5
    """
    metric_rules = [
        {
            "category": "Order Creation",
            "name": "Normal Order Creation",
            "metric_type": "count",
            "regex": r"Normal Order Creation\s*([0-9,]+(?:\.\d+)?)",
            "unit": "orders",
        },
        {
            "category": "Order Creation",
            "name": "Pending / Processing status",
            "metric_type": "latest value",
            "regex": r"Pending / Processing status\s*([0-9,]+(?:\.\d+)?)",
            "unit": "orders",
        },
    ]

    rows = build_rows(page_text, metric_rules)

    assert rows[0]["value"] == "12450"
    assert rows[1]["value"] == "3.5"


def test_default_metrics_match_real_dashboard_label_variants():
    page_text = """
    Customer creation sync to CRM - Trend 12
    Shipment result processing error monitor 4
    Shipment instruction Cron Error monitor 7
    """

    rules = {
        "Customer creation sync to CRM": "Customer creation sync to CRM",
        "Shipment result processing error": "Shipment result processing error",
        "Shipment instruction Cron Error": "Shipment instruction Cron Error",
    }

    for rule_name, expected_text in rules.items():
        matching_rule = next(rule for rule in get_metrics() if rule.name == rule_name)
        assert re.search(matching_rule.regex, page_text, re.IGNORECASE)


def test_zero_values_are_not_dropped_from_report():
    page_text = """
    Pending / Processing status 0
    """
    rows = build_rows(page_text, [{
        "category": "Order Creation",
        "name": "Pending / Processing status",
        "metric_type": "latest value",
        "regex": r"Pending / Processing status\s*([0-9,]+(?:\.\d+)?)",
        "unit": "orders",
    }])

    assert rows[0]["value"] == "0"


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

    def fake_query(self, account_id, query):
        return [{"count": 42}]

    monkeypatch.setattr(NewRelicDashboardClient, "_query_nrql", fake_query)

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

    def fake_query(self, account_id, query):
        return [
            {"count": 8, "endTimeSeconds": 1_760_000_000},
            {"count": 0, "endTimeSeconds": 1_760_000_060},
        ]

    monkeypatch.setattr(NewRelicDashboardClient, "_query_nrql", fake_query)
    rows = client.extract_from_dashboard_json()

    assert [(row["metric_type"], row["value"], row["timestamp"]) for row in rows] == [
        ("latest value", 8, "2025-10-09 08:53:20 UTC"),
        ("trend", 8, "2025-10-09 08:53:20 UTC"),
    ]
    assert all(row["category"] == "Monitoring / Order Creation" for row in rows)


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

    def fake_query(self, account_id, query):
        if account_id == "101":
            raise RuntimeError("mock API failure")
        return []

    monkeypatch.setattr(NewRelicDashboardClient, "_query_nrql", fake_query)
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

    def fake_query(self, account_id, query):
        return [{"count": 7}]

    monkeypatch.setattr(NewRelicDashboardClient, "_query_nrql", fake_query)

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

    def fake_query(self, account_id, query):
        return [{"count": 1}]

    monkeypatch.setattr(NewRelicDashboardClient, "_query_nrql", fake_query)

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

    def fake_query(self, account_id, query):
        calls.append((account_id, query))
        return [{"count": 2}]

    monkeypatch.setattr(NewRelicDashboardClient, "_query_nrql", fake_query)
    rows = client.extract_from_dashboard_json()

    assert len(rows) == len(calls) == 20
    assert all(account_id == "6538703" for account_id, _ in calls)
    assert all(row["account_id"] == "6538703" for row in rows)
    assert rows[0]["category"] == "Order Creation"


def test_real_dashboard_export_keeps_all_rows_when_api_queries_fail(monkeypatch, tmp_path):
    dashboard_path = os.path.join(os.path.dirname(__file__), "..", "dashboard.json")
    client = object.__new__(NewRelicDashboardClient)
    client.settings = {"dashboard_json": dashboard_path, "account_id": ""}

    def failed_query(self, account_id, query):
        raise RuntimeError("simulated API failure")

    monkeypatch.setattr(NewRelicDashboardClient, "_query_nrql", failed_query)
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


def test_run_raises_clear_error_when_dashboard_json_and_api_key_missing(tmp_path):
    client = object.__new__(NewRelicDashboardClient)
    client.settings = {
        "dashboard_json": "",
        "api_key": "",
        "dashboard_url": "https://one.newrelic.com/dashboards/detail/test",
        "output_path": str(tmp_path / "report.xlsx"),
    }

    with pytest.raises(RuntimeError, match="NEW_RELIC_DASHBOARD_JSON.*NEW_RELIC_API_KEY"):
        client.run()


def test_get_runtime_settings_requires_required_env(monkeypatch):
    for key in ["NEW_RELIC_DASHBOARD_URL", "NEW_RELIC_USERNAME", "NEW_RELIC_PASSWORD"]:
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("NEW_RELIC_DASHBOARD_URL", "")
    monkeypatch.setenv("NEW_RELIC_USERNAME", "user@example.com")
    monkeypatch.setenv("NEW_RELIC_PASSWORD", "secret")

    with pytest.raises(ValueError, match="Missing required environment variable"):
        get_runtime_settings()
