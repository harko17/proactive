from __future__ import annotations

from playwright.sync_api import sync_playwright

from app.config import get_runtime_settings
from app.report import ExcelReportWriter, build_rows


class NewRelicDashboardClient:
    def __init__(self):
        self.settings = get_runtime_settings()

    def login(self, page):
        page.goto(self.settings["base_url"], wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)

        login_link = page.locator("text=Log in").first
        if login_link.count() > 0:
            login_link.click(timeout=20000)

        username_selector = (
            "input[type='email'], "
            "input[name*='email'], "
            "input[name='login'], "
            "input[id*='login']"
        )
        password_selector = (
            "input[type='password'], "
            "input[name*='password'], "
            "input[id*='password']"
        )

        page.locator(username_selector).first.wait_for(timeout=20000)
        page.fill(username_selector, self.settings["username"])
        page.fill(password_selector, self.settings["password"])

        submit_button = page.locator(
            "button[type='submit'], input[type='submit'], button:has-text('Sign in')"
        )
        if submit_button.count() > 0:
            submit_button.first.click(timeout=20000)

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
