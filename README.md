# Proactive

A small Python automation that reads a New Relic dashboard export, queries its NRQL widgets, and saves the results to an Excel spreadsheet.

It is intended to run on a schedule (for example via cron) and keep a daily or hourly report of the metrics you care about.

## What the app does

- Reads the dashboard JSON export or falls back to a browser login flow
- Extracts widget titles and NRQL queries from the dashboard configuration without hardcoded metric lists
- Queries New Relic via the NerdGraph GraphQL API with a configured API key and configurable reporting window
- Selects the latest non-zero result for `latest value` and `trend` metrics, retaining the matching time-series timestamp
- Writes a formatted `Dashboard Summary` sheet to `output/proactive_report.xlsx`, including category, visualization, account, metric type, value, and result status
- Supports scheduled execution through GitHub Actions

## Project structure

```text
app/
  __init__.py
  config.py              Runtime settings and metric rules
  newrelic_client.py     Browser automation entry point
  report.py              Excel report generation and value extraction
cron/
  example-cron.txt       Example scheduled task
output/                  Generated Excel reports
logs/                    Log files from cron runs
README.md
requirements.txt
.env.example
.gitignore
```

## Setup

1. Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
playwright install chromium
```

3. Copy the environment template and fill in the real values:

```bash
cp .env.example .env
```

4. Update `.env` with your New Relic credentials and, for JSON mode, your API key and dashboard export.

The project supports two modes:

- JSON mode: set `NEW_RELIC_DASHBOARD_JSON` and `NEW_RELIC_API_KEY`
- Browser mode: set `NEW_RELIC_DASHBOARD_URL`, `NEW_RELIC_USERNAME`, and `NEW_RELIC_PASSWORD`

If a dashboard query does not already specify a time window, the app appends `SINCE <NEW_RELIC_REPORTING_WINDOW>` automatically. The default is `24 hours ago`.

For metrics classified as `latest value` or `trend`, the report scans NRQL result buckets from newest to oldest and records the first positive numeric value. If no positive bucket exists, the report shows `No non-zero value` with a blank value rather than misreporting zero. Other metric types retain their normal query-result value.

## Run once

```bash
python -m app.newrelic_client
```

Alternative direct script execution also works from the project root:

```bash
python app/newrelic_client.py
```

## Example cron job

```cron
0 * * * * cd /path/to/proactive && source .venv/bin/activate && python -m app.newrelic_client >> logs/proactive.log 2>&1
```

## Notes

- The dashboard URL, username, and password are required.
- If New Relic's DOM changes, update the regex metric rules in `app/config.py`.
- Do not commit `.env`; keep credentials in a secrets manager or local environment configuration.
