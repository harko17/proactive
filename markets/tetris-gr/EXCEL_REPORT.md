# Tetris GR Excel report format

Fill in the expected workbook layout for Tetris GR. The implementation will use this specification for the report title, metric labels, ordering, categories, and formatting.

## Workbook and sheet

- Workbook/report title: Tetris GR - Monitoring charts
- Worksheet name:
- Header text and placement:

## Columns and rows

| Order | Column/header | Required content or example |
| --- | --- | --- |
| 1 |  |  |
| 2 |  |  |
| 3 |  |  |

## Grouping and formatting

- Category/group rows and merge behavior:
- Metric/value selection rules, including zero and time-series behavior:
- Fonts, colors, borders, alignment, widths, and number formats:
- Rows or fields that must always appear, even with no data:

## Example layout

Paste a small Markdown table or attach a screenshot showing the expected report layout.

+------------------+----------------------------------------------------+--------------+-------+
| Tetris GR - Monitoring charts |  | Monitoring |  |
+------------------+----------------------------------------------------+--------------+-------+
| Order Monitor    | Stuck in Pending Status                            | trend        |     0 |
|                  | Stuck in Processing Status                         | trend        |     0 |
|                  | Stuck in Distributor unavailable                   | trend        |     0 |
|                  | Closed orders                                      | trend        |     0 |
|                  | Inventory Monitor - Inventory Update Failure       | latest value | 2.51k |
+------------------+----------------------------------------------------+--------------+-------+
| Product Monitor  | Product Monitor - New SKU found                    | trend        |     0 |
|                  | Product Monitor - New SKU with Hyphen found        | trend        |     0 |
+------------------+----------------------------------------------------+--------------+-------+
| Customer Monitor | Company Pending Approval - Company not Active      | trend        |     1 |
|                  | Duplicate POS Code                                 | trend        |     7 |
|                  | Duplicate OL IDs                                   | trend        |     2 |
|                  | Address verification - Dot Address in Second Line  | trend        |     0 |
|                  | Inventory Source - Inventory source not assigned   | trend        |     0 |
|                  | for Outlets                                        |              |       |
+------------------+----------------------------------------------------+--------------+-------+