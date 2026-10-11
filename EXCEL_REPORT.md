# Excel report generation

The application sends each market's exact GraphQL request from `markets/<market>/CURLS.md` to `https://api.newrelic.com/graphql` and writes live response values to `output/<market>.xlsx`. Saved market responses are for reference and tests only; they are never used as production data.

## Data and result mapping

Each market request contains aliased NRQL queries. The parser supports both `account(id: ...) { nrql(query: ...) }` and `nrql(accounts: [...], query: ...)` NerdGraph request shapes. Every alias stays associated with the account ID from its own request selection. The market's `EXCEL_REPORT.md` controls the visible title, category, metric label, type, and order where those are shown. Queries not named in the example layout remain in the workbook as additional rows; layout entries without a corresponding query remain visible with an empty value.

Response results may contain aggregate counts such as `{"count": 15}` or time-series buckets such as:

```json
[
  {"beginTimeSeconds": 1791686399, "endTimeSeconds": 1791688199, "count": 0},
  {"beginTimeSeconds": 1791688199, "endTimeSeconds": 1791689999, "count": 0},
  {"beginTimeSeconds": 1791689999, "endTimeSeconds": 1791691799, "count": 1},
  {"beginTimeSeconds": 1791691799, "endTimeSeconds": 1791693599, "count": 0}
]
```

For timestamped buckets, the app scans from newest to oldest and reports the latest non-zero metric value—in this example, `1`—along with that bucket's timestamp. It recognizes count-shaped keys including `count`, `count.message`, `uniqueCount.message`, and case-insensitive result aliases such as `Counts`. Timestamp fields are excluded from metric extraction.

- A single aggregate `{"count": 0}` is a real result and is written as numeric zero.
- If every time-series bucket is zero, the report shows `0` and keeps the latest bucket timestamp.
- A failed GraphQL query produces a blank cell and a warning; the run fails after saving the report rather than presenting a failed query as zero.

## Workbook layout

Each **Dashboard Summary** sheet has four columns:

| Column | Contents |
| --- | --- |
| A | Monitoring category |
| B | Widget title |
| C | `count`, `latest value`, or `trend` |
| D | Numeric value from the API, including `0` when every series bucket is zero; blank when no usable numeric result exists |

The title row and category placement follow that market's example layout. The saved workbook keeps all query rows, including zeroes and blank unavailable values. Account IDs, status, and timestamps remain in the internal result rows so the visible workbook retains the compact dashboard-like layout.

## Run and credentials

Set `NEW_RELIC_API_KEY` to a New Relic User API key. GitHub Actions expects it as the repository secret with exactly that name. The GraphQL endpoint is fixed to `https://api.newrelic.com/graphql`. A failed query leaves that widget's value blank, saves the affected report for diagnosis, and fails the run so it cannot be mistaken for a zero.

Run all configured markets locally with:

```bash
python -m app.newrelic_client
```
