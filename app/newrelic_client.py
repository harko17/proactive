from __future__ import annotations

import json
import re
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

try:
    from app.config import get_metrics, get_runtime_settings
    from app.report import ExcelReportWriter, build_rows
except ImportError:  # pragma: no cover - allows running the file directly
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from app.config import get_metrics, get_runtime_settings
    from app.report import ExcelReportWriter, build_rows


class NewRelicDashboardClient:
    def __init__(self):
        self.settings = get_runtime_settings()

    def _find_first(self, page, selectors):
        for selector in selectors:
            locator = page.locator(selector).first
            if locator.count() > 0:
                return locator
        return None

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

    def _query_nrql(self, account_id: str, query: str):
        api_key = self.settings.get("api_key")
        if not api_key:
            raise ValueError("NEW_RELIC_API_KEY is required when using dashboard JSON / NRQL mode")

        effective_query = self._apply_reporting_window(query, self.settings.get("reporting_window", "24 hours ago"))
        endpoint = self.settings.get("graphql_endpoint") or "https://api.newrelic.com/graphql"
        payload = {
            "query": "query($q: String!) { actor { account(id: %s) { nrql(query: $q) { results } } } }" % int(account_id),
            "variables": {"q": effective_query},
        }

        retries = 3
        for attempt in range(retries + 1):
            try:
                response = requests.post(
                    endpoint,
                    headers={"API-Key": api_key, "Content-Type": "application/json"},
                    json=payload,
                    timeout=(10, 60),
                )
            except requests.RequestException as exc:
                if attempt >= retries:
                    raise RuntimeError(f"New Relic GraphQL request failed for account {account_id}: {exc}") from exc
                time.sleep(2 ** attempt)
                continue

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                if attempt >= retries:
                    raise RuntimeError(f"New Relic API rate limit exceeded for account {account_id}: {response.text}")
                delay = float(retry_after) if retry_after and retry_after.replace(".", "", 1).isdigit() else 2 ** attempt
                time.sleep(delay)
                continue

            if response.status_code in {500, 502, 503, 504}:
                if attempt >= retries:
                    raise RuntimeError(f"New Relic API server error for account {account_id}: HTTP {response.status_code}")
                delay = 2 ** attempt
                time.sleep(delay)
                continue

            if response.status_code in {401, 403}:
                raise RuntimeError(
                    "New Relic authentication failed. Verify NEW_RELIC_API_KEY and that it can query account "
                    f"{account_id}."
                )

            if response.status_code >= 400:
                raise RuntimeError(
                    f"New Relic GraphQL request failed for account {account_id}: HTTP {response.status_code} {response.text}"
                )

            try:
                data = response.json()
            except ValueError as exc:
                raise RuntimeError(f"New Relic GraphQL response for account {account_id} was not valid JSON: {response.text}") from exc

            errors = data.get("errors")
            if errors:
                raise RuntimeError(f"New Relic API query failed for account {account_id}: {errors}")

            return data.get("data", {}).get("actor", {}).get("account", {}).get("nrql", {}).get("results", [])

        raise RuntimeError(f"New Relic GraphQL request did not complete for account {account_id}")

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

        return value

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

        if not values:
            fallback = (self.settings or {}).get("account_id")
            if fallback:
                values.append(str(fallback).strip())

        ordered = []
        seen = set()
        for account_id in values:
            if account_id and account_id not in seen:
                ordered.append(account_id)
                seen.add(account_id)
        return ordered

    def extract_from_dashboard_json(self):
        dashboard_json = self.settings.get("dashboard_json") or ""
        if not dashboard_json:
            return []

        dashboard = json.loads(self._load_dashboard_json(dashboard_json))
        rows = []
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
                raw_config = widget.get("rawConfiguration") or {}
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
                if not queries:
                    warnings.warn(f"Skipping widget '{title}' on page '{page_name}' because it has no NRQL queries")
                    continue

                for query_index, query_data in enumerate(queries):
                    if not isinstance(query_data, dict):
                        warnings.warn(
                            f"Skipping NRQL query #{query_index + 1} for widget '{title}' on page '{page_name}' because it is not a JSON object"
                        )
                        continue

                    nrql_query = (query_data.get("query") or "").strip()
                    if not nrql_query:
                        warnings.warn(f"Skipping empty NRQL query #{query_index + 1} for widget '{title}' on page '{page_name}'")
                        continue

                    account_ids = self._iter_account_ids(query_data)
                    if not account_ids:
                        warnings.warn(
                            f"Skipping widget '{title}' on page '{page_name}' because no account ID is associated with the query"
                        )
                        continue

                    for account_id in account_ids:
                        try:
                            result = self._query_nrql(str(account_id), nrql_query)
                        except Exception as exc:  # pragma: no cover - exercised via mocked API responses in tests
                            warnings.warn(
                                f"Failed to query widget '{title}' on page '{page_name}' for account {account_id}: {exc}"
                            )
                            continue

                        metric_type = self._metric_type(title, nrql_query, visualization)
                        if metric_type.lower() in {"latest value", "trend"}:
                            value, timestamp = self._extract_latest_nonzero(result)
                            status = "OK" if value is not None else "No non-zero value"
                        else:
                            value = self._extract_value(result)
                            timestamp = None
                            status = "OK" if value is not None else "No numeric result"

                        if timestamp is None:
                            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

                        rows.append(
                            {
                                "timestamp": timestamp,
                                "dashboard_name": dashboard_name,
                                "dashboard_url": self.settings.get("dashboard_url", ""),
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
                        )

        return rows

    def login(self, page):
        page.goto(self.settings["base_url"], wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)

        login_selectors = [
            "a:has-text('Log in')",
            "button:has-text('Log in')",
            "a:has-text('Sign in')",
            "button:has-text('Sign in')",
            "[data-testid*='login']",
        ]
        login_link = self._find_first(page, login_selectors)
        if login_link is not None:
            try:
                login_link.click(timeout=20000)
            except Exception:
                pass

        page.wait_for_timeout(3000)

        username_selectors = [
            "input[type='email']",
            "input[name='login']",
            "input[name='username']",
            "input[name*='email']",
            "input[id*='login']",
            "input[id*='email']",
            "input[name*='user']",
        ]
        password_selectors = [
            "input[type='password']",
            "input[name='password']",
            "input[name*='password']",
            "input[id*='password']",
        ]

        username_field = self._find_first(page, username_selectors)
        if username_field is not None:
            username_field.wait_for(timeout=20000)
            username_field.fill(self.settings["username"])

            continue_button = page.locator(
                "button:has-text('Continue'), button:has-text('Next'), button:has-text('Submit'), button:has-text('Sign in'), button:has-text('Log in'), input[type='submit']"
            ).first
            if continue_button.count() > 0:
                try:
                    continue_button.click(timeout=20000)
                except Exception:
                    pass

            page.wait_for_timeout(2500)

        password_field = self._find_first(page, password_selectors)
        if password_field is None:
            for selector in password_selectors:
                try:
                    page.wait_for_selector(selector, timeout=30000)
                    password_field = self._find_first(page, password_selectors)
                    if password_field is not None:
                        break
                except Exception:
                    continue

        if username_field is None and password_field is None:
            debug_inputs = []
            for selector in username_selectors + password_selectors:
                for candidate in page.locator(selector).all():
                    debug_inputs.append(
                        candidate.evaluate(
                            "el => ({type: el.type, name: el.name, id: el.id, placeholder: el.placeholder, value: el.value})"
                        )
                    )
            raise RuntimeError(
                "New Relic login form did not render as expected. "
                f"Checked selectors: {username_selectors + password_selectors}. "
                f"Found inputs: {debug_inputs}"
            )

        if password_field is not None:
            password_field.wait_for(timeout=20000)
            password_field.fill(self.settings["password"])

        submit_button = page.locator(
            "button[type='submit'], input[type='submit'], button:has-text('Sign in'), button:has-text('Log in'), button:has-text('Continue'), button:has-text('Next')"
        ).first
        if submit_button.count() > 0:
            try:
                submit_button.click(timeout=20000)
            except Exception:
                pass

        page.wait_for_load_state("networkidle", timeout=90000)

    def open_dashboard(self, page):
        dashboard_url = self.settings["dashboard_url"]
        page.goto(dashboard_url, wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(7000)

    def extract(self, page):
        page_text = page.locator("body").inner_text()
        metric_rules = [
            {
                "category": rule.category,
                "name": rule.name,
                "metric_type": rule.metric_type,
                "regex": rule.regex,
                "unit": rule.unit,
            }
            for rule in self.settings["metrics"]
        ]
        return build_rows(page_text, metric_rules)

    def run(self):
        dashboard_json = self.settings.get("dashboard_json") or ""
        api_key = self.settings.get("api_key") or ""
        dashboard_url = self.settings.get("dashboard_url") or ""
        username = self.settings.get("username") or ""
        password = self.settings.get("password") or ""

        if not dashboard_json and not api_key:
            raise RuntimeError(
                "No New Relic data source is configured. Set NEW_RELIC_DASHBOARD_JSON and NEW_RELIC_API_KEY. "
                "The browser fallback is disabled because it silently produces empty reports in CI."
            )

        if dashboard_json:
            if not api_key:
                raise RuntimeError(
                    "NEW_RELIC_DASHBOARD_JSON is configured, but NEW_RELIC_API_KEY is missing. "
                    "Provide a valid New Relic API key to query the dashboard widgets."
                )
            rows = self.extract_from_dashboard_json()
            print(f"Dashboard JSON detected: length={len(dashboard_json)}")
            print(f"Rows extracted from dashboard JSON: {len(rows)}")
            if rows:
                for row in rows[:5]:
                    print(row)
        elif dashboard_url:
            if not username or not password:
                raise RuntimeError(
                    "Browser-mode execution requires NEW_RELIC_USERNAME and NEW_RELIC_PASSWORD when no dashboard JSON is supplied."
                )
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1600, "height": 1200})
                self.login(page)
                self.open_dashboard(page)
                rows = self.extract(page)
                browser.close()
        else:
            raise RuntimeError(
                "No New Relic data source is configured. Set NEW_RELIC_DASHBOARD_JSON and NEW_RELIC_API_KEY. "
                "The browser fallback is disabled because it silently produces empty reports in CI."
            )

        writer = ExcelReportWriter(self.settings["output_path"])
        report_path = writer.write(rows)
        return report_path


if __name__ == "__main__":
    client = NewRelicDashboardClient()
    report_path = client.run()
    print(f"Report generated: {report_path}")
