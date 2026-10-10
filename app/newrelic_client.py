from __future__ import annotations

import json
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

try:
    from app.config import get_runtime_settings
    from app.report import ExcelReportWriter, build_rows
except ImportError:  # pragma: no cover - allows running the file directly
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from app.config import get_runtime_settings
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

    def _query_nrql(self, account_id: str, query: str):
        api_key = self.settings.get("api_key")
        if not api_key:
            raise ValueError("NEW_RELIC_API_KEY is required when using dashboard JSON / NRQL mode")

        payload = {
            "query": "query($q: String!) { actor { account(id: %s) { nrql(query: $q) { results } } } }" % int(account_id),
            "variables": {"q": query},
        }
        response = requests.post(
            "https://api.newrelic.com/graphql",
            headers={"API-Key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        errors = data.get("errors")
        if errors:
            raise RuntimeError(f"New Relic API query failed: {errors}")

        return data.get("data", {}).get("actor", {}).get("account", {}).get("nrql", {}).get("results", [])

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

    def extract_from_dashboard_json(self):
        dashboard_json = self.settings.get("dashboard_json") or ""
        if not dashboard_json:
            return []

        dashboard_path = Path(dashboard_json)
        if dashboard_path.exists():
            dashboard_json = dashboard_path.read_text(encoding="utf-8")

        dashboard = json.loads(dashboard_json)
        rows = []

        for page in dashboard.get("pages", []):
            page_name = page.get("name", "New Relic Dashboard")
            for widget in page.get("widgets", []):
                title = (widget.get("title") or "").strip()
                raw_config = widget.get("rawConfiguration") or {}
                queries = raw_config.get("nrqlQueries") or []
                if not title or not queries:
                    continue

                for query_data in queries:
                    nrql_query = (query_data or {}).get("query")
                    if not nrql_query:
                        continue

                    account_id = (query_data or {}).get("accountId")
                    if not account_id:
                        account_ids = (query_data or {}).get("accountIds") or []
                        if account_ids:
                            account_id = account_ids[0]
                    if not account_id:
                        account_id = self.settings.get("account_id")
                    if not account_id:
                        continue

                    try:
                        result = self._query_nrql(str(account_id), nrql_query)
                    except Exception:
                        continue

                    value = self._extract_value(result)
                    if value is None:
                        continue

                    rows.append(
                        {
                            "timestamp": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "category": page_name,
                            "metric_name": title,
                            "metric_type": "nrql",
                            "value": str(value),
                            "unit": "",
                            "source": "newrelic api",
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
        if self.settings.get("dashboard_json"):
            rows = self.extract_from_dashboard_json()
        else:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1600, "height": 1200})
                self.login(page)
                self.open_dashboard(page)
                rows = self.extract(page)
                browser.close()

        writer = ExcelReportWriter(self.settings["output_path"])
        report_path = writer.write(rows)
        return report_path


if __name__ == "__main__":
    client = NewRelicDashboardClient()
    report_path = client.run()
    print(f"Report generated: {report_path}")
