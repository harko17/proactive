# Excel report generation

The application sends the exact GraphQL request in `CURLS.md` to `https://api.newrelic.com/graphql` and writes the live response values to `output/proactive_report.xlsx`. The saved response in `response.md` is for reference only; it is never used as the production data source.

## Data and result mapping

The request contains 34 aliased NRQL queries. Each alias is associated with the account ID in that query and mapped to its report label/category in `app/config.py`. The report includes every alias, including values that are zero or unavailable.

Response results may contain aggregate counts such as `{"count": 15}` or time-series buckets such as:

```json
[
  {"beginTimeSeconds": 1791686399, "endTimeSeconds": 1791688199, "count": 0},
  {"beginTimeSeconds": 1791688199, "endTimeSeconds": 1791689999, "count": 0},
  {"beginTimeSeconds": 1791689999, "endTimeSeconds": 1791691799, "count": 1},
  {"beginTimeSeconds": 1791691799, "endTimeSeconds": 1791693599, "count": 0}
]
```

For timestamped buckets, the app scans from newest to oldest and reports the latest non-zero metric value—in this example, `1`—along with that bucket's timestamp. It recognizes count-shaped keys including `count`, `count.message`, and `uniqueCount.message`. Timestamp fields are excluded from metric extraction.

- A single aggregate `{"count": 0}` is a real result and is written as numeric zero.
- An all-zero time series produces a blank value with status `No non-zero value`.
- A failed GraphQL query produces a blank cell and a warning; the run fails after saving the report rather than presenting a failed query as zero.

## Workbook layout

The **Dashboard Summary** sheet has four columns:

| Column | Contents |
| --- | --- |
| A | Monitoring category |
| B | Widget title |
| C | `count`, `latest value`, or `trend` |
| D | Numeric value from the API, or blank when no non-zero series result is available |

The title row reads **Japan - Monitoring charts** and **Monitoring**. Adjacent rows in the same category share a merged category cell. Account IDs, status, and timestamps remain in the internal result rows so the visible workbook retains the compact dashboard-like layout.

## Run and credentials

Set `NEW_RELIC_API_KEY` to a New Relic User API key. GitHub Actions expects it as the repository secret with exactly that name. The GraphQL endpoint is fixed to `https://api.newrelic.com/graphql`.

Run locally with:

```bash
python -m app.newrelic_client
```
