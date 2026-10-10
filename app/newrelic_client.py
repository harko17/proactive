from __future__ import annotations

from playwright.sync_api import sync_playwright

try:
    from app.config import get_runtime_settings
    from app.report import ExcelReportWriter, build_rows
except ImportError:  # pragma: no cover - allows running the file directly
    import sys
    from pathlib import Path

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

    def login(self, page):
        page.goto(self.settings["base_url"], wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)

        login_link = page.locator(
            "a:has-text('Log in'), button:has-text('Log in'), text=Log in, [data-testid*='login']"
        ).first
        if login_link.count() > 0:
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
        password_field = self._find_first(page, password_selectors)

        if username_field is None or password_field is None:
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

        username_field.wait_for(timeout=20000)
        username_field.fill(self.settings["username"])
        password_field.fill(self.settings["password"])

        submit_button = page.locator(
            "button[type='submit'], input[type='submit'], button:has-text('Sign in'), button:has-text('Log in')"
        ).first
        if submit_button.count() > 0:
            submit_button.click(timeout=20000)

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
