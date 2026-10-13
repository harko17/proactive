# Proactive New Relic market monitoring reports

This project submits each market's GraphQL POST from its `markets/<market>/CURLS.md` file to New Relic NerdGraph and writes one workbook per market to `output/<market>.xlsx`.

## Source of truth

- Each market's `CURLS.md` contains the exact request body and account IDs. The application reads and sends the JSON body unchanged.
- Each market's `response.md` is a saved example of the expected GraphQL response for reference; production report values always come from the live API response.
- Each market's `EXCEL_REPORT.md` supplies its visible workbook layout. The request aliases that do not appear in the example layout are still included in the workbook as additional rows.

The response parser associates each result with the matching GraphQL alias. It reads numeric result fields such as `count`, `count.message`, and `uniqueCount.message`; timestamp fields are never treated as metrics.

## Configure credentials

Add New Relic User API keys as repository secrets:

1. Open **Settings → Secrets and variables → Actions**.
2. Select **New repository secret**.
3. Set the name to `NEW_RELIC_API_KEY`.
4. Set the value to the API key itself—without quotes or an `API-Key:` prefix.

Repeat these steps for `TETRIS_API_KEY`; Tetris FR and Tetris GR use this separate key, while every other market uses `NEW_RELIC_API_KEY`. Set both environment variables for local runs. Do not commit either key.

## Run

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python -m app.newrelic_client
```

Market reports are saved to `output/<market>.xlsx`, and the cross-market summary based on `markets/overall_report.md` is saved to `output/overall_report.md`; unavailable market metrics appear as `-`. Set `OUTPUT_DIR` to change the output folder. GitHub Actions runs hourly or by manual dispatch, uploads all 14 market reports plus the overall summary, and commits them only after every market API query and report succeeds.

For a multi-bucket time series, the report scans newest to oldest and records the latest positive value and its bucket timestamp. If every bucket is zero, it reports `0` with the latest bucket timestamp. A single aggregate result of `count: 0` also remains zero. See [EXCEL_REPORT.md](./EXCEL_REPORT.md) for report details.
