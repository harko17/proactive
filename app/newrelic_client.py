from __future__ import annotations

import json
import re
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import requests

try:
    from app.config import get_metrics, get_runtime_settings
    from app.report import ExcelReportWriter
except ImportError:  # pragma: no cover - allows running the file directly
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from app.config import get_metrics, get_runtime_settings
    from app.report import ExcelReportWriter


class NewRelicDashboardClient:
    def __init__(self):
        self.settings = get_runtime_settings()

    def _send_graphql_payload(self, payload: dict, entries: list[dict]) -> dict:
        if not entries:
            return {}
        api_key = self.settings.get("api_key")
        if not api_key:
            raise ValueError("Set the NEW_RELIC_API_KEY GitHub Actions secret to query New Relic.")

        endpoint = self.settings.get("graphql_endpoint", "https://api.newrelic.com/graphql")

        for attempt in range(4):
            try:
                response = requests.post(
                    endpoint,
                    headers={"API-Key": api_key, "Content-Type": "application/json"},
                    json=payload,
                    timeout=(10, 60),
                )
            except requests.RequestException as exc:
                if attempt == 3:
                    raise RuntimeError(f"New Relic GraphQL request failed: {exc}") from exc
                time.sleep(2 ** attempt)
                continue

            if response.status_code == 429 or response.status_code in {500, 502, 503, 504}:
                if attempt == 3:
                    raise RuntimeError(f"New Relic GraphQL request failed after retries: HTTP {response.status_code}")
                retry_after = response.headers.get("Retry-After", "")
                delay = float(retry_after) if retry_after.isdigit() else 2 ** attempt
                time.sleep(delay)
                continue

            if response.status_code in {401, 403}:
                raise RuntimeError(
                    "New Relic authentication/authorization failed. Check the NEW_RELIC_API_KEY secret "
                    "and its access to all dashboard accounts."
                )
            if response.status_code >= 400:
                raise RuntimeError(f"New Relic GraphQL request failed: HTTP {response.status_code} {response.text}")

            try:
                response_data = response.json()
            except ValueError as exc:
                raise RuntimeError("New Relic returned a non-JSON GraphQL response.") from exc
            if not isinstance(response_data, dict):
                raise RuntimeError("New Relic returned a GraphQL response with an invalid JSON shape.")
            return response_data

        raise RuntimeError("New Relic GraphQL request did not complete.")

    @staticmethod
    def _extract_graphql_batch_results(response_data: dict, entries: list[dict]) -> dict:
        data = response_data.get("data")
        actor = data.get("actor") if isinstance(data, dict) else None
        errors = response_data.get("errors") or []
        alias_errors = {}
        global_errors = []
        for error in errors:
            path = error.get("path") if isinstance(error, dict) else None
            alias = path[1] if isinstance(path, list) and len(path) > 1 else None
            message = error.get("message", "GraphQL query failed") if isinstance(error, dict) else str(error)
            if alias:
                alias_errors.setdefault(alias, []).append(message)
            else:
                global_errors.append(message)

        results = {}
        for entry in entries:
            alias = entry["alias"]
            if global_errors:
                results[alias] = {"error": "; ".join(global_errors)}
                continue
            if alias in alias_errors:
                results[alias] = {"error": "; ".join(alias_errors[alias])}
                continue
            query_result = actor.get(alias) if isinstance(actor, dict) else None
            nrql = query_result.get("nrql") if isinstance(query_result, dict) else None
            values = nrql.get("results") if isinstance(nrql, dict) else None
            if isinstance(values, list):
                results[alias] = {"results": values}
            else:
                results[alias] = {"error": "Response did not contain this alias's NRQL results"}
        return results

    @staticmethod
    def _extract_value(result):
        if isinstance(result, list):
            if not result:
                return None
            return NewRelicDashboardClient._extract_value(result[-1])
        if isinstance(result, dict):
            keys = list(result)
            preferred_keys = (
                "count",
                "uniqueCount",
                "sum",
                "average",
                "max",
                "min",
                "latest",
                "total",
                "result",
                "value",
            )
            measurement_key = next((key for key in preferred_keys if key in result), None)
            if measurement_key is None:
                measurement_key = next(
                    (
                        key for prefix in ("count.", "uniqueCount.", "sum.", "average.", "max.", "min.")
                        for key in keys if key.startswith(prefix)
                    ),
                    None,
                )
            if measurement_key is not None:
                return NewRelicDashboardClient._extract_value(result[measurement_key])
            return None
        if isinstance(result, (int, float)):
            return result
        if isinstance(result, str):
            cleaned = result.strip()
            if cleaned and cleaned.lower() not in {"null", "none"}:
                return cleaned
        return None

    @staticmethod
    def _extract_latest_nonzero(result):
        if not isinstance(result, list):
            return None, None

        for item in reversed(result):
            if not isinstance(item, dict):
                continue

            value = NewRelicDashboardClient._extract_value(item)
            if isinstance(value, bool):
                continue
            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                continue
            if numeric_value <= 0:
                continue

            timestamp = next(
                (item.get(key) for key in ("endTimeSeconds", "timestamp", "time", "beginTimeSeconds") if item.get(key) is not None),
                None,
            )
            if timestamp is not None:
                try:
                    epoch = float(timestamp)
                    if abs(epoch) >= 100_000_000_000:
                        epoch /= 1000
                    timestamp = datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                except (TypeError, ValueError, OSError, OverflowError):
                    timestamp = str(timestamp)
            return value, timestamp

        return None, None

    @staticmethod
    def _extract_report_value(result):
        timestamped_buckets = (
            isinstance(result, list)
            and bool(result)
            and all(
                isinstance(item, dict)
                and any(key in item for key in ("beginTimeSeconds", "endTimeSeconds", "timestamp", "time"))
                for item in result
            )
        )
        if timestamped_buckets:
            value, timestamp = NewRelicDashboardClient._extract_latest_nonzero(result)
            if value is None:
                return None, None, "No non-zero value"
            return value, timestamp, "OK"

        value = NewRelicDashboardClient._extract_value(result)
        return value, None, "OK" if value is not None else "No numeric result"

    @staticmethod
    def _dashboard_row(
        dashboard_name: str,
        dashboard_url: str,
        page_name: str,
        category: str,
        title: str,
        visualization: str,
        metric_type: str,
        account_id: str = "",
        value=None,
        timestamp: str | None = None,
        status: str = "No numeric result",
    ) -> dict:
        return {
            "timestamp": timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "dashboard_name": dashboard_name,
            "dashboard_url": dashboard_url,
            "page": page_name,
            "category": category,
            "metric_name": title,
            "metric_type": metric_type,
            "value": value,
            "unit": "",
            "source": "newrelic api",
            "account_id": str(account_id),
            "visualization": visualization,
            "status": status,
        }

    def _load_curl_request(self) -> tuple[dict, list[dict]]:
        curl_path = Path(self.settings["curl_file"])
        curl_document = curl_path.read_text(encoding="utf-8")
        body_match = re.search(r"\$body\s*=\s*@'\s*\r?\n([\s\S]*?)\r?\n'@", curl_document)
        if not body_match:
            raise ValueError(f"Could not find the --data-raw JSON body in {curl_path}")
        payload = json.loads(body_match.group(1))
        if not isinstance(payload, dict):
            raise ValueError(f"The cURL request body in {curl_path} must be a JSON object")
        graphql_query = payload.get("query")
        if not isinstance(graphql_query, str):
            raise ValueError(f"The cURL request in {curl_path} has no GraphQL query")

        selection_pattern = re.compile(
            r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*account\(id:\s*(\d+)\)\s*"
            r"\{\s*nrql\(query:\s*(\"(?:\\.|[^\"\\])*\")\)\s*\{\s*results\s*\}\s*\}"
        )
        entries = []
        for alias, account_id, encoded_nrql in selection_pattern.findall(graphql_query):
            if int(account_id) <= 0:
                raise ValueError(f"Invalid New Relic account ID {account_id!r} for alias {alias!r}")
            metric = next((item for item in get_metrics() if item.alias == alias), None)
            if metric is None:
                raise ValueError(f"No report label is configured for GraphQL alias {alias!r}")
            entries.append({
                "alias": alias,
                "account_id": account_id,
                "query": json.loads(encoded_nrql),
                "dashboard_name": "Japan",
                "page": "Monitoring",
                "category": metric.category,
                "metric_name": metric.name,
                "visualization": "",
                "metric_type": metric.metric_type,
            })

        expected_aliases = {item.alias for item in get_metrics()}
        actual_aliases = {entry["alias"] for entry in entries}
        if len(entries) != len(expected_aliases) or actual_aliases != expected_aliases:
            missing = sorted(expected_aliases - actual_aliases)
            unexpected = sorted(actual_aliases - expected_aliases)
            raise ValueError(
                f"GraphQL widget set in {curl_path} is incomplete or has duplicates "
                f"(missing={missing}, unexpected={unexpected})"
            )
        entries.sort(key=lambda entry: next(
            index for index, metric in enumerate(get_metrics()) if metric.alias == entry["alias"]
        ))
        return payload, entries

    def _rows_from_graphql_response(self, response_data: dict, entries: list[dict]) -> list[dict]:
        results_by_alias = self._extract_graphql_batch_results(response_data, entries)
        rows = []
        for entry in entries:
            result = results_by_alias[entry["alias"]]
            if "error" in result:
                warnings.warn(
                    f"Query failed for widget '{entry['metric_name']}' "
                    f"and account {entry['account_id']}: {result['error']}"
                )
                row = self._dashboard_row(
                    entry["dashboard_name"], "", entry["page"], entry["category"],
                    entry["metric_name"], entry["visualization"], entry["metric_type"],
                    account_id=entry["account_id"], status="Query failed",
                )
            else:
                value, timestamp, status = self._extract_report_value(result["results"])
                row = self._dashboard_row(
                    entry["dashboard_name"], "", entry["page"], entry["category"],
                    entry["metric_name"], entry["visualization"], entry["metric_type"],
                    account_id=entry["account_id"], value=value, timestamp=timestamp, status=status,
                )
            rows.append(row)
        return rows

    def run(self):
        payload, entries = self._load_curl_request()
        response = self._send_graphql_payload(payload, entries)
        rows = self._rows_from_graphql_response(response, entries)
        print(f"Japan dashboard query rows prepared: {len(rows)}")
        writer = ExcelReportWriter(self.settings["output_path"])
        report_path = writer.write(rows)
        failed_rows = [
            row for row in rows
            if row.get("status") not in {"OK", "No numeric result", "No non-zero value"}
        ]
        if failed_rows:
            raise RuntimeError(
                f"{len(failed_rows)} dashboard row(s) could not be queried successfully. "
                f"The report with blank unavailable values "
                f"was saved to {report_path}."
            )
        return report_path


if __name__ == "__main__":
    client = NewRelicDashboardClient()
    report_path = client.run()
    print(f"Report generated: {report_path}")
