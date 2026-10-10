import os

import pytest

from app.config import get_runtime_settings
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
