# Excel report generation

The application reads the checked-in `dashboard.json`, queries its NRQL widgets through New Relic NerdGraph, and writes `output/proactive_report.xlsx`. The API endpoint is `https://api.newrelic.com/graphql`; the only credential is `NEW_RELIC_API_KEY`, sent as the `API-Key` HTTP header.

## Data flow

1. The dashboard export supplies the dashboard name, page and widget titles, markdown category headings, NRQL text, and account IDs.
2. The client skips markdown widgets as report values, but uses their headings as categories. It retains rows for non-markdown widgets even when query configuration, account IDs, or usable result values are missing.
3. Every valid query/account pair is included in one GraphQL POST as an aliased `account(id: ...) { nrql(query: $variable) { results } }` selection. The account ID remains paired with that query.
4. GraphQL `results` are mapped back to the widget row using the response alias. Values are extracted from actual results; API errors do not become numeric zeroes.
5. The Excel writer renders each query/account row in the `Dashboard Summary` sheet.

The committed `dashboard.json` must be the intended New Relic dashboard export. The API key must have access to every account referenced by its query definitions.

## Workbook layout

The workbook has one sheet, **Dashboard Summary**:

| Column | Contents |
| --- | --- |
| A | Category from dashboard markdown headings |
| B | Widget title |
| C | Metric type (`count`, `latest value`, or `trend`) |
| D | Numeric result, or blank when no usable result exists |

The first row contains the dashboard title and “Monitoring.” Category cells are merged across consecutive widgets in the same category. Account ID, query status, and source timestamp remain part of the internal row model rather than adding columns to the compact workbook.

## Result selection and time window

- A single aggregate response such as `{"count": 0}` is reported as numeric zero.
- For multiple timestamped result buckets, buckets are scanned newest to oldest and the latest positive numeric value is selected with its timestamp.
- If every timestamped bucket is zero, the value is blank and status is `No non-zero value`.
- Missing or failed query results stay blank; query failures are warned about, and the run fails after saving the workbook so Actions does not report a false success.
- A query's explicit NRQL time range is retained. When it has no `SINCE`, `UNTIL`, or `COMPARE` clause, `SINCE 24 hours ago` is added.

## Preview

The sample values below illustrate the layout only; report values come from the API response.

| Japan - Monitoring charts |  | **Monitoring** |  |
| --- | --- | --- | ---: |
| Order Creation | Normal Order Creation | count | 312 |
|  | Pending / Processing status | latest value | 9 |
|  | Awaiting shipment | latest value | 9 |
|  | Awaiting Capture / Payment review | latest value | 1 |
|  | Pending Payment Cancellations | count | 0 |

The category shown in column A is merged in Excel when adjacent rows share it.
