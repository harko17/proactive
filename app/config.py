from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv()


def _read_env(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or "").strip()


PROJECT_ROOT = Path(__file__).resolve().parent.parent
NEW_RELIC_GRAPHQL_ENDPOINT = "https://api.newrelic.com/graphql"
NEW_RELIC_REPORTING_WINDOW = "24 hours ago"
NEW_RELIC_DASHBOARD_JSON = PROJECT_ROOT / "dashboard.json"


@dataclass(frozen=True)
class MetricRule:
    name: str
    metric_type: str


DEFAULT_METRICS: List[MetricRule] = [
    MetricRule("Normal Order Creation", "count"),
    MetricRule("Pending / Processing status", "latest value"),
    MetricRule("Awaiting shipment", "latest value"),
    MetricRule("Awaiting Capture / Payment review", "latest value"),
    MetricRule("Pending Payment Cancellations", "count"),
    MetricRule("Shipment instruction Cron monitor", "trend"),
    MetricRule("Shipment instruction Cron Error", "count"),
    MetricRule("Shipment result processing monitor", "trend"),
    MetricRule("Shipment result processing error", "count"),
    MetricRule("Order Status Import Error Monitor", "count"),
    MetricRule("Customer creation sync to CRM", "trend"),
    MetricRule("Customer Sync to Magento - Error", "count"),
    MetricRule("Award Coupon API failure", "count"),
    MetricRule("Product Update Pricebook error", "count"),
    MetricRule("Award Points API failure", "count"),
    MetricRule("Orders yet to sync downstream", "latest value"),
    MetricRule("SiteCore API failure", "count"),
    MetricRule("Sagawa Express API Error", "count"),
    MetricRule("Award Badge API failure", "count"),
    MetricRule("Customer creation/update Error", "count"),
    MetricRule("Customer creation yet to sync Sitecore/CRM", "latest value"),
    MetricRule("Abandoned Cart Update Error", "count"),
    MetricRule("Product Update Error", "count"),
    MetricRule("Back in Stock Notification Error", "count"),
    MetricRule("Order create/ update event error", "count"),
    MetricRule("Order create event - Trend", "trend"),
    MetricRule("Order confirmation email", "trend"),
    MetricRule("Shipment confirmation email", "trend"),
    MetricRule("Stock Process File Monitor", "trend"),
    MetricRule("Age unverified customer order count", "latest value"),
]


def get_metrics() -> List[MetricRule]:
    return DEFAULT_METRICS


def get_runtime_settings() -> dict:
    api_key = _read_env("NEW_RELIC_API_KEY")
    if not api_key:
        raise ValueError("Missing required environment variable: NEW_RELIC_API_KEY")
    return {
        "graphql_endpoint": NEW_RELIC_GRAPHQL_ENDPOINT,
        "reporting_window": NEW_RELIC_REPORTING_WINDOW,
        "dashboard_json": str(NEW_RELIC_DASHBOARD_JSON),
        "api_key": api_key,
        "output_path": _read_env("OUTPUT_PATH", str(PROJECT_ROOT / "output" / "proactive_report.xlsx")),
        "metrics": get_metrics(),
    }
