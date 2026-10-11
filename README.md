# Proactive Japan monitoring report

This project submits the GraphQL POST documented in [CURLS.md](./CURLS.md) to New Relic NerdGraph and writes the returned NRQL counts to `output/proactive_report.xlsx`.

## Source of truth

- `CURLS.md` contains the exact request body, all 34 widget aliases, their NRQL queries, and their New Relic account IDs. The application reads that body and sends it unchanged.
- `response.md` is a saved example of the expected GraphQL response for reference; production report values always come from the live API response.
- Widget names, report categories, and metric types are defined in `app/config.py`; query strings and account IDs are not duplicated there.

The response parser associates each result with the matching GraphQL alias. It reads numeric result fields such as `count`, `count.message`, and `uniqueCount.message`; timestamp fields are never treated as metrics.

## Configure credentials

The only required New Relic credential is a User API key. Add it as a repository secret:

1. Open **Settings → Secrets and variables → Actions**.
2. Select **New repository secret**.
3. Set the name to `NEW_RELIC_API_KEY`.
4. Set the value to the API key itself—without quotes or an `API-Key:` prefix.

The same environment variable can be set for a local run. Do not commit the real key.

## Run

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python -m app.newrelic_client
```

The output path defaults to `output/proactive_report.xlsx`; set `OUTPUT_PATH` to change it. GitHub Actions runs hourly or by manual dispatch, uploads the workbook, and commits it only after a successful API/report run.

For a multi-bucket time series, the report scans newest to oldest and records the latest positive value and its bucket timestamp. If all buckets are zero, the value is blank. A single aggregate result of `count: 0` remains zero. See [EXCEL_REPORT.md](./EXCEL_REPORT.md) for report details.
