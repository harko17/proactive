# VELO IT Excel report format

Describe the required workbook appearance for this market. Replace the prompts below with the exact labels, order, and examples to use when implementing the report.

## Workbook and sheet

- Workbook/report title: `[fill in]`
- Worksheet name: `[fill in]`
- Header text and placement: `[fill in]`

## Columns and rows

| Order | Column/header | Required content or example |
| --- | --- | --- |
| 1 | `[fill in]` | `[fill in]` |
| 2 | `[fill in]` | `[fill in]` |
| 3 | `[fill in]` | `[fill in]` |

## Grouping and formatting

- Category/group rows and merge behavior: `[fill in]`
- Metric/value selection rules, including zero and time-series behavior: `[fill in]`
- Fonts, colors, borders, alignment, widths, and number formats: `[fill in]`
- Any rows or fields that must always appear, even with no data: `[fill in]`

## Example layout

Paste a small Markdown table or attach a screenshot that shows the expected report layout.

+----------------------------------------+-------------------------------------+--------------+---+
| VELO IT - Monitoring charts            |                                     | Monitoring   |   |
+----------------------------------------+-------------------------------------+--------------+---+
| Order Creation                         | Normal Order Creation               | trend        | 0 |
+----------------------------------------+-------------------------------------+--------------+---+
| Order Fulfillment                      | Pending / Processing status         | latest value | 0 |
+----------------------------------------+-------------------------------------+--------------+---+
| Order Fulfillment                      | Pending Payment                     | latest value | 0 |
+----------------------------------------+-------------------------------------+--------------+---+
| Integration                            | Customer creation sync to CRM       | trend        | 0 |
+----------------------------------------+-------------------------------------+--------------+---+
| Integration                            | Customer without SF ID              | latest value | 0 |
+----------------------------------------+-------------------------------------+--------------+---+
| Integration                            | Order creation sync to CRM - Trend  | trend        | 0 |
+----------------------------------------+-------------------------------------+--------------+---+
| Transactional Email                    | Account confirmation email          | trend        | 1 |
+----------------------------------------+-------------------------------------+--------------+---+
| Transactional Email                    | Order confirmation email            | trend        | 0 |
+----------------------------------------+-------------------------------------+--------------+---+
| Transactional Email                    | Shipment confirmation email         | trend        | 0 |
+----------------------------------------+-------------------------------------+--------------+---+
| Age Verification/Account Confirmation  | Age unverified customer order count | count        | 0 |
+----------------------------------------+-------------------------------------+--------------+---+