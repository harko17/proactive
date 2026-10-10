from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook


class ExcelReportWriter:
    def __init__(self, output_path: str):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, rows: list[dict]) -> str:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "New Relic Metrics"

        headers = [
            "timestamp",
            "category",
            "metric_name",
            "metric_type",
            "value",
            "unit",
            "source",
        ]
        sheet.append(headers)

        for row in rows:
            sheet.append(
                [
                    row.get("timestamp", ""),
                    row.get("category", ""),
                    row.get("metric_name", ""),
                    row.get("metric_type", ""),
                    row.get("value", ""),
                    row.get("unit", ""),
                    row.get("source", ""),
                ]
            )

        workbook.save(self.output_path)
        return str(self.output_path)


def normalize_value(raw_value: str) -> str:
    value = raw_value.strip()
    value = value.replace(",", "")
    value = value.replace("%", "")
    value = value.replace(" ", "")

    if value.lower().endswith("k"):
        value = str(float(value[:-1]) * 1000)
    elif value.lower().endswith("m"):
        value = str(float(value[:-1]) * 1000000)

    if value.endswith(".0"):
        value = value[:-2]

    return value


def extract_metric_value(page_text: str, metric_rule: dict) -> str:
    pattern = metric_rule.get("regex", "")
    if not pattern:
        return ""

    match = re.search(pattern, page_text, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""

    value = match.group(1).strip()
    return normalize_value(value)


def build_rows(page_text: str, metric_rules: list[dict]) -> list[dict]:
    rows: list[dict] = []
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    for rule in metric_rules:
        value = extract_metric_value(page_text, rule)
        if value != "":
            rows.append(
                {
                    "timestamp": timestamp,
                    "category": rule.get("category", ""),
                    "metric_name": rule.get("name", ""),
                    "metric_type": rule.get("metric_type", ""),
                    "value": value,
                    "unit": rule.get("unit", ""),
                    "source": "newrelic dashboard",
                }
            )

    return rows
