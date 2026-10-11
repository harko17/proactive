# GLO IT Excel report format

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

+----------------------------------------+----------------------------------------------+--------------+-------+
| GLO IT - Monitoring charts             |                                              | Monitoring   |       |
+----------------------------------------+----------------------------------------------+--------------+-------+
| Order Creation                         | Normal Order Creation                        | trend        |     2 |
+----------------------------------------+----------------------------------------------+--------------+-------+
| Order Fulfillment                      | Pending / Processing status                  | latest value |    90 |
|                                        | Pending Payment                              | latest value |     2 |
|                                        | Order fulfillment - Shipment Import Error    | count        |     0 |
|                                        | Order fulfillment - HOG Order Export         | latest value |     1 |
|                                        | Order fulfillment - Shipment Import          | latest value |     0 |
|                                        | Order creation to CRM - Trend                | trend        |     1 |
|                                        | Order fulfillment - Order Export             | latest value |     1 |
|                                        | Order create/ update event error             | count        |   146 |
+----------------------------------------+----------------------------------------------+--------------+-------+
| Integration                            | Customer creation sync to CRM - trend        | trend        |     1 |
|                                        | SharpEnd Customer creation Error             | count        |     0 |
|                                        | Customer Loyalty CRM update - Error          | count        |       |
|                                        | Customer without SF ID                       | latest value |    30 |
|                                        | Customer creation sync to CRM - Error        | count        |    44 |
|                                        | Customer update to CRM error                 | count        |     0 |
|                                        | Device Registration error                    | count        | 8.59k |
|                                        | Customer Sync to Magento - Error             | count        |   950 |
|                                        | Fanize api request Error                     | count        |    93 |
|                                        | SMS api request Error                        | count        |     0 |
+----------------------------------------+----------------------------------------------+--------------+-------+
| Transactional Email                    | Account confirmation email                   | trend        |     0 |
|                                        | Order confirmation email                     | trend        |     2 |
|                                        | Shipment confirmation email                  | trend        |     0 |
|                                        | Invoice email                                | trend        |     0 |
+----------------------------------------+----------------------------------------------+--------------+-------+
| Age Verification/Account Confirmation  | Age unverified customer order count          | count        |     0 |
|                                        | Yoti Age verification invalid response       | count        |     0 |
|                                        | Yoti Age verification unsuccessful response  | count        |     7 |
|                                        | Yoti API failure                             | count        |     0 |
|                                        | Yoti Doc Scan API Error                      | count        |     0 |
|                                        | Yoti Doc scan Unable to create session       | count        |     0 |
+----------------------------------------+----------------------------------------------+--------------+-------+