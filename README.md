# Proactive New Relic market monitoring reports

This project submits each market's GraphQL POST from its `markets/<market>/CURLS.md` file to New Relic NerdGraph and writes one workbook per market to `output/<market>.xlsx`.

## Source of truth

- Each market's `CURLS.md` contains the exact request body and account IDs. The application reads and sends the JSON body unchanged.
- Each market's `response.md` is a saved example of the expected GraphQL response for reference; production report values always come from the live API response.
- Each market's `EXCEL_REPORT.md` supplies its visible workbook layout. The request aliases that do not appear in the example layout are still included in the workbook as additional rows.

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

Reports are saved to `output/<market>.xlsx`; set `OUTPUT_DIR` to change the output folder. GitHub Actions runs hourly or by manual dispatch, uploads all generated workbooks, and commits them only after every market API query and report succeeds.

For a multi-bucket time series, the report scans newest to oldest and records the latest positive value and its bucket timestamp. If every bucket is zero, it reports `0` with the latest bucket timestamp. A single aggregate result of `count: 0` also remains zero. See [EXCEL_REPORT.md](./EXCEL_REPORT.md) for report details.
