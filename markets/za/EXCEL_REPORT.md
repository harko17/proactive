# ZA Excel report format

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

╔══════════════════╦═════════════════════════════════════════════╦════════════╦═══╗
║                  ║ ZA - Monitoring charts                      ║ Monitoring ║   ║
╠══════════════════╬═════════════════════════════════════════════╬════════════╬═══╣
║ Order Fulfillment║ Pending Payment Cancellations               ║ count      ║ 0 ║
║                  ║ Order fullfilment Request - Failures        ║ count      ║ 0 ║
║                  ║ Order fullfilment Request - Failures to read║ count      ║ 0 ║
║                  ║ response                                    ║            ║   ║
║                  ║ Shipment creation                           ║ count      ║ 31║
║                  ║ Shipment creation error                     ║ count      ║ 0 ║
╠══════════════════╬═════════════════════════════════════════════╬════════════╬═══╣
║ Integration      ║ Customer Sync to Magento - Error            ║ count      ║ 20║
║                  ║ Contact Form - Error                        ║ count      ║ 1 ║
║                  ║ Inventory Sync error                        ║ count      ║ 0 ║
╚══════════════════╩═════════════════════════════════════════════╩════════════╩═══╝