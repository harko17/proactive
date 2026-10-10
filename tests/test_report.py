import os
import re

import pytest

from app.config import get_metrics, get_runtime_settings
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
