# How the Excel report is generated

The application creates `output/proactive_report.xlsx` using the dashboard JSON export and live NRQL results from New Relic. The workbook is written by `app/report.py`; widget parsing and API querying happen in `app/newrelic_client.py`.

## Data flow

1. The application reads the dashboard JSON from `NEW_RELIC_DASHBOARD_JSON` (either JSON text or a path to a JSON file).
2. It visits every page and widget, skipping markdown widgets and widgets without executable NRQL queries.
3. Each query is sent to New Relic NerdGraph using the account ID associated with that query. A query with multiple account IDs is queried once for each account.
4. Results are read from the API response. The workbook does not derive live values from dashboard configuration or hardcoded metric values.
5. A row is prepared for each successfully executed query/account pair and written to the `Dashboard Summary` sheet.

If an API request fails, the application emits a warning and skips that query/account row. If the API returns an empty or non-numeric result, the report records a blank value and a status describing the result; it does not substitute zero.

## Workbook layout

The workbook contains one sheet, **Dashboard Summary**:

- Row 1: the dashboard title spans columns A-B; `Monitoring` appears in column C. If a dashboard URL is configured, the title links to it.
- Row 2 onward: one row per query/account result.
- Consecutive rows in the same category share one vertically merged category cell.

| Column | Contents |
| --- | --- |
| A | Category, such as Order Creation, Order Fulfillment, or Integration |
| B | Widget title |
| C | Metric type, such as `count`, `latest value`, or `trend` |
| D | Numeric value from the New Relic query |

The sheet has light-blue title cells, thin black grid borders, centered merged category labels, and right-aligned numeric values. Numeric values are stored as Excel numbers where possible. Query/account identity and result status are kept in the application logs/row model rather than adding extra visible columns to this compact layout.

## Preview

The generated workbook will look approximately like this in Excel. The values below are examples only; real report values come from the NRQL API responses. The sample is shortened to show the layout.

| Japan - Monitoring charts |  | **Monitoring** |  |
| --- | --- | --- | ---: |
| Order Creation | Normal Order Creation | count | 312 |
|  | Pending / Processing status | latest value | 0 |
|  | Awaiting shipment | latest value | 9 |
|  | Awaiting Capture / Payment review | latest value | 0 |
|  | Pending Payment Cancellations | count | 0 |
|  | Shipment instruction Cron monitor | trend | 15 |
|  | Shipment instruction Cron Error monitor | count | 0 |
| Order Fulfillment | Shipment result processing monitor | trend | 0 |
|  | Shipment result processing error monitor | count | 0 |
| Integration | Customer creation sync to CRM - Trend | trend | 271 |
|  | Customer Sync to Magento - Error | count | 0 |
| Transactional Email and Inventory | Order confirmation email | trend | 299 |
|  | Shipment confirmation email | trend | 0 |
| Age Verification/Account Confirmation | Age unverified customer order count | latest value | 0 |

In Excel, each repeated category is vertically merged and centered over its widget rows; the markdown preview repeats the category in the first cell only to represent that merged area.

## Value selection

For metrics classified as **latest value** or **trend**, the application scans the NRQL result array from the last item to the first. It selects the first item whose numeric value is greater than zero. The value is taken from that result item and its timestamp is retained when supplied by New Relic.

- If a later bucket is zero, the search continues to an earlier bucket with a positive value.
- If all result buckets are zero, `Value` is blank and `Status` is `No non-zero value`.
- For other metric types, the application uses the existing general result extraction logic; a legitimate zero remains zero.
- If no numeric result is available, `Value` is blank and `Status` is `No numeric result`.

Metric type is first matched against configured metric rules in `app/config.py`. For unmatched widgets, a `TIMESERIES` query or `viz.line` visualization is classified as `trend`; other unmatched widgets default to `count`.

## Time range

The query retains any time range already present in its NRQL. If it has no `SINCE`, `UNTIL`, or `COMPARE` clause, the application adds `SINCE <NEW_RELIC_REPORTING_WINDOW>`. The default is `24 hours ago`.

## Output location and run

The output defaults to:

```text
output/proactive_report.xlsx
```

Override the location with `OUTPUT_PATH`. Run the report from the repository root with:

```bash
python -m app.newrelic_client
```

In GitHub Actions, the generated workbook is uploaded as the `proactive-report` artifact.
