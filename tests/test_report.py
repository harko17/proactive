import json
import os
import re

import pytest

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
    assert rows[0]["value"] == "42"


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
    assert rows[0]["value"] == "7"


def test_extract_from_dashboard_json_filters_za_monitoring_widgets(monkeypatch):
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

    assert "Normal Order Creation" not in metric_names
    assert "Account confirmation email" not in metric_names
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
    saved_path = writer.write([{"timestamp": "now", "category": "Test", "metric_name": "Test metric", "metric_type": "count", "value": "42", "unit": "items", "source": "unit test"}])

    assert saved_path == str(target)
    assert target.exists()


def test_get_runtime_settings_requires_required_env(monkeypatch):
    for key in ["NEW_RELIC_DASHBOARD_URL", "NEW_RELIC_USERNAME", "NEW_RELIC_PASSWORD"]:
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("NEW_RELIC_DASHBOARD_URL", "")
    monkeypatch.setenv("NEW_RELIC_USERNAME", "user@example.com")
    monkeypatch.setenv("NEW_RELIC_PASSWORD", "secret")

    with pytest.raises(ValueError, match="Missing required environment variable"):
        get_runtime_settings()
