# GLO DE Excel report format

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

╔═══════════════════════════════╦══════════════════════════════════════════════╦══════════════╦════╗
║ GLO -DE - Monitoring charts   ║                                              ║ Monitoring   ║    ║
╠═══════════════════════════════╬══════════════════════════════════════════════╬══════════════╬════╣
║ Order Fulfillment             ║ Pending / Processing status                  ║ latest value ║  2 ║
║                               ║ Awaiting shipment                            ║ latest value ║  2 ║
║                               ║ Awaiting Capture / Payment review            ║ latest value ║  0 ║
║                               ║ Device-trial Payment pending charge          ║ latest value ║ 52 ║
║                               ║ Order fullfilment Request - Upload to courier║ latest value ║  0 ║
║                               ║ failed                                       ║              ║    ║
╠═══════════════════════════════╬══════════════════════════════════════════════╬══════════════╬════╣
║ Integration                   ║ Customer without SF ID                       ║ latest value ║  0 ║
║                               ║ consent_retry_cron Execution Monitoring      ║ latest value ║  7 ║
╠═══════════════════════════════╬══════════════════════════════════════════════╬══════════════╬════╣
║ Transactional Email           ║ Duplicate order confirmation email sent      ║ latest value ║  0 ║
╠═══════════════════════════════╬══════════════════════════════════════════════╬══════════════╬════╣
║ Age Verification/Account      ║ Age unverified customer order count          ║ latest value ║  0 ║
║ Confirmation                  ║ Account confirmation pending monitor         ║ latest value ║  0 ║
╚═══════════════════════════════╩══════════════════════════════════════════════╩══════════════╩════╝