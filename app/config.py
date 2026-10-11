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
NEW_RELIC_CURLS_FILE = PROJECT_ROOT / "CURLS.md"


@dataclass(frozen=True)
class MetricRule:
    alias: str
    name: str
    category: str
    metric_type: str


DEFAULT_METRICS: List[MetricRule] = [
    MetricRule("normalOrderCreation", "Normal Order Creation", "Order Creation", "count"),
    MetricRule("awaitingCapturePaymentReview", "Awaiting Capture / Payment review", "Order Creation", "latest value"),
    MetricRule("pendingProcessingStatus", "Pending / Processing status", "Order Creation", "latest value"),
    MetricRule("awaitingShipment", "Awaiting shipment", "Order Creation", "latest value"),
    MetricRule("pendingPaymentCancellations", "Pending Payment Cancellations", "Order Creation", "count"),
    MetricRule("shipmentInstructionCronMonitor", "Shipment instruction Cron monitor", "Order Fulfillment", "trend"),
    MetricRule("shipmentInstructionCronErrorMonitor", "Shipment instruction Cron Error monitor", "Order Fulfillment", "count"),
    MetricRule("shipmentResultProcessingMonitor", "Shipment result processing monitor", "Order Fulfillment", "trend"),
    MetricRule("shipmentResultProcessingErrorMonitor", "Shipment result processing error monitor", "Order Fulfillment", "count"),
    MetricRule("orderStatusImportErrorMonitor", "Order Status Import Error Monitor", "Order Fulfillment", "count"),
    MetricRule("jpOrderShippedStatus", "JP Order Shipped Status", "Order Fulfillment", "trend"),
    MetricRule("deviceTrialPaymentPendingCharge", "Device Trial Payment Pending Charge", "Order Fulfillment", "trend"),
    MetricRule("customerCreationSyncToCrmTrend", "Customer creation sync to CRM - Trend", "Integration", "trend"),
    MetricRule("customerSyncToMagentoError", "Customer Sync to Magento - Error", "Integration", "count"),
    MetricRule("awardCouponApiFailure", "Award Coupon API failure", "Integration", "count"),
    MetricRule("productUpdatePricebookError", "Product Update Pricebook error", "Integration", "count"),
    MetricRule("awardPointsApiFailure", "Award Points API failure", "Integration", "count"),
    MetricRule("ordersYetToSyncDownstream", "Orders yet to sync downstream", "Integration", "latest value"),
    MetricRule("sitecoreApiFailure", "SiteCore API failure", "Integration", "count"),
    MetricRule("sagawaExpressApiError", "Sagawa Express API Error", "Integration", "count"),
    MetricRule("awardBadgeApiFailure", "Award Badge API failure", "Integration", "count"),
    MetricRule("customerCreationUpdateError", "Customer creation/update Error", "Integration", "count"),
    MetricRule("customerCreationYetToSyncSitecoreCrm", "Customer creation yet to sync Sitecore/CRM", "Integration", "latest value"),
    MetricRule("abandonedCartUpdateError", "Abandoned Cart Update Error", "Integration", "count"),
    MetricRule("productUpdateError", "Product Update Error", "Integration", "count"),
    MetricRule("backInStockNotificationError", "Back in Stock Notification Error", "Integration", "count"),
    MetricRule("orderCreateUpdateEventError", "Order create/update event error", "Integration", "count"),
    MetricRule("orderCreateEventTrend", "Order create event - Trend", "Integration", "trend"),
    MetricRule("ordersYetToSyncDownstream2", "Orders yet to sync downstream (time series)", "Integration", "trend"),
    MetricRule("docomoOutboundApiCall", "Docomo outbound API call", "Integration", "count"),
    MetricRule("orderConfirmationEmail", "Order confirmation email", "Transactional Email and Inventory", "trend"),
    MetricRule("shipmentConfirmationEmail", "Shipment confirmation email", "Transactional Email and Inventory", "trend"),
    MetricRule("stockProcessFileMonitor", "Stock Process File Monitor", "Transactional Email and Inventory", "trend"),
    MetricRule("ageUnverifiedCustomerOrderCount", "Age unverified customer order count", "Age Verification/Account Confirmation", "latest value"),
]


def get_metrics() -> List[MetricRule]:
    return DEFAULT_METRICS


def get_runtime_settings() -> dict:
    api_key = _read_env("NEW_RELIC_API_KEY")
    if not api_key:
        raise ValueError("Missing required environment variable: NEW_RELIC_API_KEY")
    return {
        "graphql_endpoint": NEW_RELIC_GRAPHQL_ENDPOINT,
        "curl_file": str(NEW_RELIC_CURLS_FILE),
        "api_key": api_key,
        "output_path": _read_env("OUTPUT_PATH", str(PROJECT_ROOT / "output" / "proactive_report.xlsx")),
        "metrics": get_metrics(),
    }
