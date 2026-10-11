# GLO PL Excel report format

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

╔═══════════════════════════════╦══════════════════════════════════════════════╦══════════════╦═════╗
║ GLO -PL - Monitoring charts   ║                                              ║ Monitoring   ║     ║
╠═══════════════════════════════╬══════════════════════════════════════════════╬══════════════╬═════╣
║ Order Fulfillment             ║ Pending / Processing status                  ║ latest value ║   3 ║
║                               ║ Awaiting shipment                            ║ latest value ║   3 ║
║                               ║ Awaiting capture / payment review            ║ latest value ║  14 ║
║                               ║ Order fullfilment Request - Upload to courier║ latest value ║   1 ║
║                               ║ failed                                       ║              ║     ║
║                               ║ Shipment creation error                      ║ count        ║   0 ║
╠═══════════════════════════════╬══════════════════════════════════════════════╬══════════════╬═════╣
║ Integration                   ║ Customer Sync to Magento - Error             ║ count        ║ 352 ║
║                               ║ Inventory Sync - Error                       ║ count        ║   0 ║
╠═══════════════════════════════╬══════════════════════════════════════════════╬══════════════╬═════╣
║ Age Verification/Account      ║ Age unverified customer order count          ║ count        ║   0 ║
║ Confirmation                  ║ Account confirmation pending monitor         ║ latest value ║   0 ║
║                               ║ Customer without SF ID                       ║ latest value ║   2 ║
╚═══════════════════════════════╩══════════════════════════════════════════════╩══════════════╩═════╝