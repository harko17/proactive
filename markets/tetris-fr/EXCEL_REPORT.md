# Tetris FR Excel report format

Fill in the expected workbook layout for Tetris FR. The implementation will use this specification for the report title, metric labels, ordering, categories, and formatting.

## Workbook and sheet

- Workbook/report title: Tetris FR - Monitoring charts
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
| Tetris FR - Monitoring charts |  | Monitoring |  |
+------------------+----------------------------------------------------+--------------+-------+
| Order Monitor    | Stuck in Pending Status                            | trend        |     4 |
|                  | Stuck in Processing Status                         | trend        |    22 |
|                  | Stuck in accepted status for more than 3 days      | trend        |   248 |
|                  | Stuck in partially accepted status for more than 3 | trend        |     2 |
|                  | days                                               |              |       |
|                  | Closed orders                                      | trend        |     0 |
|                  | Order not updated in Magento                       | trend        |     0 |
|                  | No Delivery Date                                   | trend        |     0 |
|                  | Inventory Monitor - Inventory Update Failure       | latest value | 2.61K |
+------------------+----------------------------------------------------+--------------+-------+
| Product Monitor  | Product Monitor - New SKU found                    | trend        |     0 |
|                  | Product Monitor - New SKU with Hyphen found        | trend        |     0 |
|                  | No Matricule code                                  | trend        |     0 |
+------------------+----------------------------------------------------+--------------+-------+
| Customer Monitor | Duplicate OL IDs                                   | trend        |     0 |
|                  | Address verification - Dot Address in Second Line  | trend        |     0 |
|                  | Duplicate POS Code                                 | trend        |     0 |
|                  | Company Pending Approval - Company not Active      | trend        |     0 |
|                  | Inventory Source - Inventory source not assigned   | trend        |     3 |
|                  | for Outlets                                        |              |       |
|                  | Postcode with space                                | trend        |     0 |
+------------------+----------------------------------------------------+--------------+-------+
| General Monitor  | Recapcha validation failed                         | trend        |     0 |
|                  | Service Bus Error from AIS response                | trend        |     0 |
|                  | Too many request limit reached                     | trend        |     0 |
|                  | SendGrid Authentication error                      | trend        |     0 |
|                  | Logged in user count                               | trend        |    16 |
|                  | Change of Ownership Count                          | trend        |     0 |
|                  | Points Transfer Count                              | trend        |     0 |
+------------------+----------------------------------------------------+--------------+-------+