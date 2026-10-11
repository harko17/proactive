# Proactive

Generate an Excel report from a checked-in New Relic dashboard JSON export and live NRQL results from New Relic NerdGraph.

## Data and credentials

- `dashboard.json` is the source of truth for widget names, NRQL queries, and the account ID attached to each query. Replace it with the export for the dashboard you want to report on.
- The only New Relic credential required is a New Relic **User API key**. Do not put the key in `dashboard.json` or commit a populated `.env`.
- The app sends one GraphQL POST to `https://api.newrelic.com/graphql`, using an `API-Key` header and JSON request body. Each dashboard query is sent as a GraphQL alias with its own account ID and NRQL variable.
- NRQL queries retain their own time range. Queries without one get `SINCE 24 hours ago`.

### GitHub Actions setup

Add one repository secret:

1. Open **Settings → Secrets and variables → Actions**.
2. Select **New repository secret**.
3. Set **Name** to `NEW_RELIC_API_KEY`.
4. Set **Secret** to the New Relic User API key value (paste the key only; no quotes or `API-Key:` prefix).

The workflow uses the dashboard JSON committed in the repository. Confirm that `dashboard.json` contains the intended dashboard export and that the API key can query every account ID in it. The workflow runs hourly and can also be started manually. It uploads the workbook as an artifact; it commits a report only when all New Relic queries succeed.

For a local run, install dependencies and provide `NEW_RELIC_API_KEY` in the process environment or an untracked `.env` file. `.env.example` shows the single required variable.

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python -m app.newrelic_client
```

The workbook is written to `output/proactive_report.xlsx`. Set `OUTPUT_PATH` to override its location.

For timestamped NRQL results, the report scans from newest to oldest and selects the latest non-zero bucket. If all buckets are zero, the value stays blank; a single aggregate result of `count: 0` remains zero. See [EXCEL_REPORT.md](./EXCEL_REPORT.md) for the workbook layout and result-selection rules.
