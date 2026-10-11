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

    @staticmethod
    def _apply_reporting_window(query: str, reporting_window: str = "24 hours ago") -> str:
        query_text = (query or "").strip()
        if not query_text:
            return query_text
        if re.search(r"\bSINCE\b|\bUNTIL\b|\bCOMPARE\b", query_text, flags=re.IGNORECASE):
            return query_text
        if re.search(r"\bTIMESERIES\b", query_text, flags=re.IGNORECASE):
            return re.sub(r"\bTIMESERIES\b", f"SINCE {reporting_window} TIMESERIES", query_text, count=1, flags=re.IGNORECASE)
        return f"{query_text} SINCE {reporting_window}"

    @staticmethod
    def _build_graphql_batch(entries: list[dict], reporting_window: str) -> tuple[str, dict]:
        definitions = []
        selections = []
        variables = {}
        for index, entry in enumerate(entries):
            alias = f"metric_{index}"
            variable = f"nrql_{index}"
            account_id = str(entry["account_id"])
            if not account_id.isdigit() or int(account_id) <= 0:
                raise ValueError(f"Invalid New Relic account ID in dashboard configuration: {account_id!r}")
            definitions.append(f"${variable}: String!")
            selections.append(
                f"{alias}: account(id: {int(account_id)}) "
                f"{{ nrql(query: ${variable}) {{ results }} }}"
            )
            variables[variable] = NewRelicDashboardClient._apply_reporting_window(
                entry["query"], reporting_window
            )
            entry["alias"] = alias

        graphql_query = (
            f"query DashboardMetrics({', '.join(definitions)}) "
            f"{{ actor {{ {' '.join(selections)} }} }}"
        )
        return graphql_query, variables

    def _query_nrql_batch(self, entries: list[dict]) -> dict:
        if not entries:
            return {}
        api_key = self.settings.get("api_key")
        if not api_key:
            raise ValueError("Set the NEW_RELIC_API_KEY GitHub Actions secret to query New Relic.")

        graphql_query, variables = self._build_graphql_batch(
            entries, self.settings.get("reporting_window", "24 hours ago")
        )
        payload = {"query": graphql_query, "variables": variables}
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
            return self._extract_graphql_batch_results(response_data, entries)

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
            for key in ("count", "result", "value", "total", "latest", "average", "max", "min", "sum"):
                if key in result:
                    return NewRelicDashboardClient._extract_value(result[key])
            if len(result) == 1:
                return NewRelicDashboardClient._extract_value(next(iter(result.values())))
            for value in result.values():
                parsed = NewRelicDashboardClient._extract_value(value)
                if parsed is not None:
                    return parsed
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
    def _metric_type(title: str, query: str, visualization: str) -> str:
        normalized_title = NewRelicDashboardClient._normalize_widget_title(title)
        for rule in get_metrics():
            normalized_rule = NewRelicDashboardClient._normalize_widget_title(rule.name)
            if normalized_title == normalized_rule or normalized_title.startswith(f"{normalized_rule} "):
                return rule.metric_type

        if re.search(r"\bTIMESERIES\b", query, flags=re.IGNORECASE) or visualization == "viz.line":
            return "trend"
        if re.search(r"\blatest\s*\(", query, flags=re.IGNORECASE):
            return "latest value"
        return "count"

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

    @staticmethod
    def _normalize_widget_title(title: str) -> str:
        if not title:
            return ""
        return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()

    @staticmethod
    def _load_dashboard_json(raw_dashboard_json: str) -> str:
        value = (raw_dashboard_json or "").strip()
        if not value:
            return ""

        if value.startswith("{") or value.startswith("["):
            return value

        dashboard_path = Path(value)
        if dashboard_path.exists():
            return dashboard_path.read_text(encoding="utf-8")

        raise FileNotFoundError(f"Dashboard JSON file not found: {dashboard_path}")

    def _iter_account_ids(self, query_data: dict):
        if not isinstance(query_data, dict):
            return []

        values = []
        for field in ("accountId", "accountIds"):
            candidate = query_data.get(field)
            if candidate is None:
                continue
            if isinstance(candidate, list):
                for item in candidate:
                    if item is not None:
                        values.append(str(item).strip())
            else:
                values.append(str(candidate).strip())

        ordered = []
        seen = set()
        for account_id in values:
            if account_id and account_id not in seen:
                ordered.append(account_id)
                seen.add(account_id)
        return ordered

    def extract_from_dashboard_json(self):
        dashboard_json = self.settings["dashboard_json"]
        dashboard = json.loads(self._load_dashboard_json(dashboard_json))
        ordered_items = []
        entries = []
        dashboard_name = dashboard.get("name") or "New Relic Dashboard"

        for page in dashboard.get("pages", []) or []:
            if not isinstance(page, dict):
                continue
            page_name = (page.get("name") or "New Relic Dashboard").strip() or "New Relic Dashboard"
            category = page_name
            category_headings = []
            widgets = page.get("widgets", []) or []

            for widget_index, widget in enumerate(widgets):
                if not isinstance(widget, dict):
                    warnings.warn(f"Skipping widget #{widget_index} on page '{page_name}' because it is not a JSON object")
                    continue

                title = (widget.get("title") or "").strip() or f"Untitled widget {widget_index + 1}"
                raw_config = widget.get("rawConfiguration")
                if not isinstance(raw_config, dict):
                    raw_config = {}
                visualization_data = widget.get("visualization")
                visualization = visualization_data.get("id", "") if isinstance(visualization_data, dict) else ""
                if visualization == "viz.markdown":
                    markdown_text = raw_config.get("text") or ""
                    headings = re.findall(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$", markdown_text, flags=re.MULTILINE)
                    for marker, heading in headings:
                        heading = heading.strip()
                        level = len(marker)
                        if "dashboard" in heading.lower():
                            category_headings = []
                            continue
                        category_headings = [
                            entry for entry in category_headings if entry[0] < level
                        ]
                        category_headings.append((level, heading))
                    category = " / ".join(heading for _, heading in category_headings) or page_name
                    continue

                queries = raw_config.get("nrqlQueries") or []
                if not isinstance(queries, list):
                    queries = [queries]
                if not queries:
                    warnings.warn(f"Skipping widget '{title}' on page '{page_name}' because it has no NRQL queries")
                    ordered_items.append(
                        self._dashboard_row(
                            dashboard_name,
                            "",
                            page_name,
                            category,
                            title,
                            visualization,
                            self._metric_type(title, "", visualization),
                            status="No NRQL query",
                        )
                    )
                    continue

                for query_index, query_data in enumerate(queries):
                    if not isinstance(query_data, dict):
                        warnings.warn(
                            f"NRQL query #{query_index + 1} for widget '{title}' on page '{page_name}' is not a JSON object"
                        )
                        ordered_items.append(
                            self._dashboard_row(
                                dashboard_name,
                                "",
                                page_name,
                                category,
                                title,
                                visualization,
                                self._metric_type(title, "", visualization),
                                status="Invalid NRQL configuration",
                            )
                        )
                        continue

                    nrql_query = (query_data.get("query") or "").strip()
                    if not nrql_query:
                        warnings.warn(f"Skipping empty NRQL query #{query_index + 1} for widget '{title}' on page '{page_name}'")
                        ordered_items.append(
                            self._dashboard_row(
                                dashboard_name,
                                "",
                                page_name,
                                category,
                                title,
                                visualization,
                                self._metric_type(title, "", visualization),
                                status="Empty NRQL query",
                            )
                        )
                        continue

                    account_ids = self._iter_account_ids(query_data)
                    if not account_ids:
                        warnings.warn(
                            f"No account ID is associated with widget '{title}' on page '{page_name}'"
                        )
                        ordered_items.append(
                            self._dashboard_row(
                                dashboard_name,
                                "",
                                page_name,
                                category,
                                title,
                                visualization,
                                self._metric_type(title, nrql_query, visualization),
                                status="No account ID",
                            )
                        )
                        continue

                    for account_id in account_ids:
                        if not str(account_id).isdigit() or int(account_id) <= 0:
                            warnings.warn(f"Invalid account ID {account_id!r} for widget '{title}'")
                            ordered_items.append(
                                self._dashboard_row(
                                    dashboard_name, "", page_name, category, title, visualization,
                                    self._metric_type(title, nrql_query, visualization),
                                    account_id=str(account_id), status="Invalid account ID"
                                )
                            )
                            continue
                        metric_type = self._metric_type(title, nrql_query, visualization)
                        entry = {
                            "account_id": str(account_id),
                            "query": nrql_query,
                            "dashboard_name": dashboard_name,
                            "page": page_name,
                            "category": category,
                            "metric_name": title,
                            "visualization": visualization,
                            "metric_type": metric_type,
                        }
                        entry["alias"] = f"metric_{len(entries)}"
                        entries.append(entry)
                        ordered_items.append(entry)

        try:
            results_by_alias = self._query_nrql_batch(entries)
        except Exception as exc:
            warnings.warn(f"New Relic batch request failed: {exc}")
            results_by_alias = {
                entry["alias"]: {"error": str(exc)}
                for entry in entries
            }

        rows = []
        for item in ordered_items:
            if "alias" not in item:
                rows.append(item)
                continue
            entry = item
            response = results_by_alias.get(entry["alias"], {"error": "No response for query"})
            if "error" in response:
                warnings.warn(
                    f"Query failed for widget '{entry['metric_name']}' and account {entry['account_id']}: {response['error']}"
                )
                row = self._dashboard_row(
                    entry["dashboard_name"], "", entry["page"], entry["category"],
                    entry["metric_name"], entry["visualization"], entry["metric_type"],
                    account_id=entry["account_id"], status="Query failed",
                )
            else:
                value, timestamp, status = self._extract_report_value(response["results"])
                row = self._dashboard_row(
                    entry["dashboard_name"], "", entry["page"], entry["category"],
                    entry["metric_name"], entry["visualization"], entry["metric_type"],
                    account_id=entry["account_id"], value=value, timestamp=timestamp, status=status,
                )
            rows.append(row)
        return rows

    def run(self):
        rows = self.extract_from_dashboard_json()
        print(f"Dashboard query rows prepared: {len(rows)}")
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
