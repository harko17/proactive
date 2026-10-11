# VUSE DE Excel report format

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

╔═══════════════════════════════╦══════════════════════════════════════════════════╦══════════════╦═══════╗
║ VUSE - DE - Monitoring charts ║                                                  ║ Monitoring   ║       ║
╠═══════════════════════════════╬══════════════════════════════════════════════════╬══════════════╬═══════╣
║ Order Fulfillment             ║ Pending / Processing status                      ║ latest value ║     3 ║
║                               ║ Awaiting shipment                                ║ latest value ║     1 ║
║                               ║ Awaiting Capture / Payment review                ║ latest value ║     0 ║
║                               ║ Device-trial Payment pending charge              ║ latest value ║     0 ║
║                               ║ Pending Payment Cancellations                    ║ count        ║ 7.29k ║
║                               ║ Order fullfilment Request - Failures             ║ count        ║     0 ║
║                               ║ Order fullfilment Request - Failures to resolve  ║ count        ║     0 ║
║                               ║ host                                             ║              ║       ║
║                               ║ Order fullfilment Request - Failures to read     ║ count        ║     0 ║
║                               ║ response                                         ║              ║       ║
║                               ║ Order fullfilment Request - Upload to courier    ║ latest value ║     1 ║
║                               ║ failed                                           ║              ║       ║
║                               ║ Shipment creation error                          ║ count        ║     0 ║
╠═══════════════════════════════╬══════════════════════════════════════════════════╬══════════════╬═══════╣
║ Integration                   ║ Customer Sync to Magento - Error                 ║ count        ║     0 ║
║                               ║ Customer without SF ID                           ║ latest value ║     2 ║
║                               ║ Inventory Sync - Error                           ║ count        ║     0 ║
╠═══════════════════════════════╬══════════════════════════════════════════════════╬══════════════╬═══════╣
║ Age Verification/Account      ║ Age unverified customer order count              ║ latest value ║     0 ║
║ Confirmation                  ║ Age verification (Shufa) - DE Age Verification   ║ count        ║     0 ║
║                               ║ failure                                          ║              ║       ║
║                               ║ Account confirmation pending monitor             ║ latest value ║     0 ║
╠═══════════════════════════════╬══════════════════════════════════════════════════╬══════════════╬═══════╣
║ Third party Integration       ║ Data flow to SAP - Error                         ║ count        ║     0 ║
║                               ║ Inspiration club API Error                       ║ count        ║   346 ║
╚═══════════════════════════════╩════════════════════════════════