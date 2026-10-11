from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass
class MetricRule:
    category: str
    name: str
    metric_type: str
    regex: str = ""
    unit: str = ""


def _required(name: str, value: str) -> str:
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _read_env(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or "").strip()


NEW_RELIC_BASE_URL = _read_env("NEW_RELIC_BASE_URL", "https://one.newrelic.com")
NEW_RELIC_GRAPHQL_ENDPOINT = _read_env("NEW_RELIC_GRAPHQL_ENDPOINT", "https://api.newrelic.com/graphql")
NEW_RELIC_REPORTING_WINDOW = _read_env("NEW_RELIC_REPORTING_WINDOW", "24 hours ago")
NEW_RELIC_DASHBOARD_URL = _read_env("NEW_RELIC_DASHBOARD_URL")
NEW_RELIC_DASHBOARD_JSON = _read_env("NEW_RELIC_DASHBOARD_JSON")
NEW_RELIC_API_KEY = _read_env("NEW_RELIC_API_KEY")
NEW_RELIC_ACCOUNT_ID = _read_env("NEW_RELIC_ACCOUNT_ID")
NEW_RELIC_USERNAME = _read_env("NEW_RELIC_USERNAME")
NEW_RELIC_PASSWORD = _read_env("NEW_RELIC_PASSWORD")
OUTPUT_PATH = _read_env("OUTPUT_PATH", "output/proactive_report.xlsx")

DEFAULT_METRICS: List[MetricRule] = [
    MetricRule("Order Creation", "Normal Order Creation", "count", r"Normal Order Creation\s*([0-9,]+(?:\.\d+)?)"),
    MetricRule("Order Creation", "Pending / Processing status", "latest value", r"Pending / Processing status\s*([0-9,]+(?:\.\d+)?)"),
    MetricRule("Order Creation", "Awaiting shipment", "latest value", r"Awaiting shipment\s*([0-9,]+(?:\.\d+)?)"),
    MetricRule("Order Creation", "Awaiting Capture / Payment review", "latest value", r"Awaiting Capture / Payment review\s*([0-9,]+(?:\.\d+)?)"),
    MetricRule("Order Creation", "Pending Payment Cancellations", "count", r"Pending Payment Cancellations\s*([0-9,]+(?:\.\d+)?)"),
    MetricRule("Order Fulfillment", "Shipment instruction Cron monitor", "trend", r"Shipment instruction Cron(?:\s*monitor|\s*Monitor)?\s*([0-9,]+(?:\.\d+)?)"),
    MetricRule("Order Fulfillment", "Shipment instruction Cron Error", "count", r"Shipment instruction Cron(?:\s*Error|\s*Error\s*monitor|\s*Error\s*Monitor)?\s*([0-9,]+(?:\.\d+)?)"),
    MetricRule("Order Fulfillment", "Shipment result processing monitor", "trend", r"Shipment result processing(?:\s*monitor|\s*Monitor)?\s*([0-9,]+(?:\.\d+)?)"),
    MetricRule("Order Fulfillment", "Shipment result processing error", "count", r"Shipment result processing(?:\s*error|\s*Error|\s*error\s*monitor|\s*Error\s*monitor)?\s*([0-9,]+(?:\.\d+)?)"),
    MetricRule("Order Fulfillment", "Order Status Import Error Monitor", "count", r"Order Status Import Error Monitor\s*([0-9,]+(?:\.\d+)?)"),
    MetricRule("Order Fulfillment", "Customer creation sync to CRM", "trend", r"Customer creation sync to CRM(?:\s*-\s*(?:Trend|trend))?\s*([0-9,]+(?:\.\d+)?)"),
    MetricRule("Order Fulfillment", "Customer Sync to Magento - Error", "count", r"Customer Sync to Magento - Error\s*([0-9,]+(?:\.\d+)?)"),
    MetricRule("Order Fulfillment", "Award Coupon API failure", "count", r"Award Coupon API failure\s*([0-9,]+(?:\.\d+)?)"),
    MetricRule("Order Fulfillment", "Product Update Pricebook error", "count", r"Product Update Pricebook error\s*([0-9,]+(?:\.\d+)?)"),
    MetricRule("Order Fulfillment", "Award Points API failure", "count", r"Award Points API failure\s*([0-9,]+(?:\.\d+)?)"),
    MetricRule("Order Fulfillment", "Orders yet to sync downstream", "latest value", r"Orders yet to sync downstream\s*([0-9,]+(?:\.\d+)?)"),
]


def get_metrics() -> List[MetricRule]:
    return DEFAULT_METRICS


def get_runtime_settings() -> dict:
    base_url = _read_env("NEW_RELIC_BASE_URL", "https://one.newrelic.com")
    graphql_endpoint = _read_env("NEW_RELIC_GRAPHQL_ENDPOINT", "https://api.newrelic.com/graphql")
    reporting_window = _read_env("NEW_RELIC_REPORTING_WINDOW", "24 hours ago")
    dashboard_url = _read_env("NEW_RELIC_DASHBOARD_URL")
    dashboard_json = _read_env("NEW_RELIC_DASHBOARD_JSON")
    api_key = _read_env("NEW_RELIC_API_KEY")
    account_id = _read_env("NEW_RELIC_ACCOUNT_ID")
    output_path = _read_env("OUTPUT_PATH", "output/proactive_report.xlsx")

    if not dashboard_url and not dashboard_json:
        raise ValueError("Missing required environment variable: NEW_RELIC_DASHBOARD_URL or NEW_RELIC_DASHBOARD_JSON")

    username = _read_env("NEW_RELIC_USERNAME")
    password = _read_env("NEW_RELIC_PASSWORD")
    if not dashboard_json and not api_key:
        username = _required("NEW_RELIC_USERNAME", username)
        password = _required("NEW_RELIC_PASSWORD", password)

    return {
        "base_url": base_url,
        "graphql_endpoint": graphql_endpoint,
        "reporting_window": reporting_window,
        "dashboard_url": dashboard_url,
        "dashboard_json": dashboard_json,
        "api_key": api_key,
        "account_id": account_id,
        "username": username,
        "password": password,
        "output_path": output_path,
        "metrics": get_metrics(),
    }
