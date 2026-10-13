from __future__ import annotations

import json
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import requests

try:
    from app.config import get_runtime_settings
    from app.market import apply_report_layout, load_request, parse_report_layout
    from app.overall_report import generate_overall_report
    from app.report import ExcelReportWriter
except ImportError:  # pragma: no cover - allows running the file directly
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from app.config import get_runtime_settings
    from app.market import apply_report_layout, load_request, parse_report_layout
    from app.overall_report import generate_overall_report
    from app.report import ExcelReportWriter


class NewRelicDashboardClient:
    def __init__(self):
        self.settings = get_runtime_settings()

    def _send_graphql_payload(
        self,
        payload: dict,
        entries: list[dict],
        api_key: str | None = None,
        api_key_name: str = "NEW_RELIC_API_KEY",
    ) -> dict:
        if not entries:
            return {}
        if api_key is None:
            settings_key = "tetris_api_key" if api_key_name == "TETRIS_API_KEY" else "api_key"
            api_key = self.settings.get(settings_key)
        if not api_key:
            raise ValueError(f"Set the {api_key_name} GitHub Actions secret to query New Relic.")

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
                    f"New Relic authentication/authorization failed. Check the {api_key_name} secret "
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
        aliases = {entry["alias"] for entry in entries}
        alias_errors = {}
        global_errors = []
        for error in errors:
            path = error.get("path") if isinstance(error, dict) else None
            alias = next(
                (part for part in path if isinstance(part, str) and part in aliases),
                None,
            ) if isinstance(path, list) else None
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
            if query_result is None and isinstance(actor, dict):
                pending = list(actor.values())
                while pending and query_result is None:
                    candidate = pending.pop()
                    if isinstance(candidate, dict):
                        if alias in candidate:
                            query_result = candidate[alias]
                        else:
                            pending.extend(candidate.values())
            nrql = query_result.get("nrql", query_result) if isinstance(query_result, dict) else None
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
                "counts",
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
            case_insensitive_keys = {key.lower(): key for key in keys}
            measurement_key = next(
                (case_insensitive_keys[key.lower()] for key in preferred_keys if key.lower() in case_insensitive_keys),
                None,
            )
            if measurement_key is None:
                measurement_key = next(
                    (
                        key for prefix in ("count.", "uniqueCount.", "sum.", "average.", "max.", "min.")
                        for key in keys if key.startswith(prefix)
                    ),
                    None,
                )
            if measurement_key is None:
                measurement_key = next(
                    (
                        key for key, value in result.items()
                        if key not in {"beginTimeSeconds", "endTimeSeconds", "timestamp", "time"}
                        and isinstance(value, (int, float))
                        and not isinstance(value, bool)
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

        all_buckets_zero = bool(result)
        latest_zero_timestamp = None
        for item in reversed(result):
            if not isinstance(item, dict):
                all_buckets_zero = False
                continue

            value = NewRelicDashboardClient._extract_value(item)
            if isinstance(value, bool):
                all_buckets_zero = False
                continue
            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                all_buckets_zero = False
                continue

            timestamp = next(
                (item.get(key) for key in ("endTimeSeconds", "timestamp", "time", "beginTimeSeconds") if item.get(key) is not None),
                None,
            )
            if numeric_value == 0 and latest_zero_timestamp is None:
                latest_zero_timestamp = timestamp
            if numeric_value < 0:
                all_buckets_zero = False
                continue
            if numeric_value == 0:
                continue
            if timestamp is not None:
                try:
                    epoch = float(timestamp)
                    if abs(epoch) >= 100_000_000_000:
                        epoch /= 1000
                    timestamp = datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                except (TypeError, ValueError, OSError, OverflowError):
                    timestamp = str(timestamp)
            return value, timestamp

        if all_buckets_zero:
            if latest_zero_timestamp is not None:
                try:
                    epoch = float(latest_zero_timestamp)
                    if abs(epoch) >= 100_000_000_000:
                        epoch /= 1000
                    latest_zero_timestamp = datetime.fromtimestamp(
                        epoch, tz=timezone.utc
                    ).strftime("%Y-%m-%d %H:%M:%S UTC")
                except (TypeError, ValueError, OSError, OverflowError):
                    latest_zero_timestamp = str(latest_zero_timestamp)
            return 0, latest_zero_timestamp

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
                return None, None, "No numeric result"
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

    def _rows_from_graphql_response(
        self,
        response_data: dict,
        entries: list[dict],
        layout: dict,
    ) -> list[dict]:
        query_entries = [entry for entry in entries if entry.get("alias")]
        results_by_alias = self._extract_graphql_batch_results(response_data, query_entries)
        rows = []
        for entry in entries:
            if not entry.get("alias"):
                rows.append(self._dashboard_row(
                    layout["title"], "", "Monitoring", entry["category"],
                    entry["metric_name"], "", entry["metric_type"],
                    status="No query configured",
                ))
                continue
            result = results_by_alias[entry["alias"]]
            if "error" in result:
                warnings.warn(
                    f"Query failed for widget '{entry['metric_name']}' "
                    f"and account {entry['account_id']}: {result['error']}"
                )
                row = self._dashboard_row(
                    layout["title"], "", "Monitoring", entry["category"],
                    entry["metric_name"], entry.get("visualization", ""), entry["metric_type"],
                    account_id=entry["account_id"], status="Query failed",
                )
            else:
                value, timestamp, status = self._extract_report_value(result["results"])
                row = self._dashboard_row(
                    layout["title"], "", "Monitoring", entry["category"],
                    entry["metric_name"], entry.get("visualization", ""), entry["metric_type"],
                    account_id=entry["account_id"], value=value, timestamp=timestamp, status=status,
                )
            rows.append(row)
        return rows

    def run(self):
        markets_root = Path(self.settings["markets_root"])
        output_dir = Path(self.settings["output_dir"])
        market_dirs = sorted(
            path for path in markets_root.iterdir()
            if path.is_dir() and (path / "CURLS.md").is_file()
        )
        if not market_dirs:
            raise RuntimeError(f"No market request files were found under {markets_root}")

        report_paths = []
        failures = []
        for market_dir in market_dirs:
            curl_path = market_dir / "CURLS.md"
            spec_path = market_dir / "EXCEL_REPORT.md"
            output_path = output_dir / f"{market_dir.name}.xlsx"
            try:
                payload, query_entries = load_request(curl_path)
                layout = parse_report_layout(spec_path, market_dir.name)
                entries = apply_report_layout(query_entries, layout)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                failures.append(f"{market_dir.name}: could not load market configuration: {exc}")
                continue

            try:
                is_tetris = market_dir.name in {"tetris-fr", "tetris-gr"}
                api_key_name = "TETRIS_API_KEY" if is_tetris else "NEW_RELIC_API_KEY"
                api_key = self.settings.get("tetris_api_key") if is_tetris else self.settings.get("api_key")
                response = self._send_graphql_payload(
                    payload,
                    query_entries,
                    api_key=api_key,
                    api_key_name=api_key_name,
                )
            except RuntimeError as exc:
                failures.append(f"{market_dir.name}: {exc}")
                response = {"data": {"actor": {}}, "errors": [{"message": str(exc)}]}

            rows = self._rows_from_graphql_response(response, entries, layout)
            writer = ExcelReportWriter(
                str(output_path),
                report_title=layout["title"],
                title_column=layout["title_column"],
                merge_categories=layout["merge_categories"],
            )
            report_path = writer.write(rows)
            report_paths.append(report_path)
            failed_rows = [
                row for row in rows
                if row.get("status") not in {"OK", "No numeric result"}
                and row.get("status") != "No query configured"
            ]
            if failed_rows:
                failures.append(
                    f"{market_dir.name}: {len(failed_rows)} row(s) failed or have no mapped query "
                    f"(report saved to {report_path})"
                )
            print(f"{market_dir.name}: prepared {len(rows)} rows -> {report_path}")

        if failures:
            raise RuntimeError("One or more market reports are incomplete:\n- " + "\n- ".join(failures))
        if len(report_paths) != len(market_dirs):
            raise RuntimeError(
                f"Generated {len(report_paths)} reports for {len(market_dirs)} configured markets"
            )
        overall_report_path = generate_overall_report(
            markets_root / "overall_report.md",
            output_dir,
            output_dir / "overall_report.xlsx",
        )
        report_paths.append(overall_report_path)
        print(f"Prepared overall report -> {overall_report_path}")
        return report_paths


if __name__ == "__main__":
    client = NewRelicDashboardClient()
    report_path = client.run()
    print(f"Report generated: {report_path}")
