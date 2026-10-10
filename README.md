# Proactive

A small Python automation that logs into New Relic, opens a dashboard, extracts a set of operational metrics from the rendered page, and saves them to an Excel spreadsheet.

It is intended to run on a schedule (for example via cron) and keep a daily or hourly report of the metrics you care about.

## What the app does

- Opens the New Relic login page
- Signs in using environment variables
- Opens a configured dashboard URL
- Extracts metric values from the page text using regex rules
- Writes the values to `output/proactive_report.xlsx`

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

4. Update `.env` with your New Relic credentials and dashboard URL.

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
