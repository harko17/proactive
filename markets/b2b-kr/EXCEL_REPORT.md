# B2B KR Excel report format

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

╔══════════════════════════════╦═══════════════════════════════╦══════════════╦═════════╗
║ B2B KR -Monitoring charts    ║                               ║ Monitoring   ║         ║
╠══════════════════════════════╬═══════════════════════════════╬══════════════╬═════════╣
║ Order Creation & Status      ║ Normal Order Creation         ║ count        ║       0 ║
║ Change                       ║ Preparing To Ship status      ║ count        ║     585 ║
║                              ║ Processing status             ║ count        ║       1 ║
╠══════════════════════════════╬═══════════════════════════════╬══════════════╬═════════╣
║ Integration                  ║ Credit update call            ║ count        ║   1.48k ║
║                              ║ Orders sent to OMS            ║ count        ║   1.47k ║
║                              ║ Credit update request error   ║ count        ║       0 ║
║                              ║ Order sent to swift           ║ count        ║   1.47k ║
║                              ║ Order confirmation received   ║ count        ║   1.47k ║
║                              ║ Order success confirmation    ║ count        ║   1.47k ║
║                              ║ Goods received update failure ║ count        ║       0 ║
║                              ║ Delivery update failure       ║ count        ║       0 ║
║                              ║ Shipment update failure       ║ count        ║       0 ║
║                              ║ Orders sent to EDA Errors     ║ count        ║       0 ║
║                              ║ Product sync                  ║ latest value ║       1 ║
║                              ║ Product price sync - Error    ║ count        ║       0 ║
║                              ║ Inventory sync                ║ count        ║     542 ║
║                              ║ Any cron job failure          ║ count        ║       0 ║
╚══════════════════════════════╩═══════════════════════════════╩══════════════╩═════════╝