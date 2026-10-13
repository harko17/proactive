# Market report specifications

Each market has a separate cURL request, response capture, and Excel layout specification. The endpoint, API-Key header, content type, and PowerShell cURL wrapper are shared; only the GraphQL JSON request body differs by market. Paste the complete market-specific body into that market's `CURLS.md`. Keep API keys out of all files.

| Market | cURL request | Response | Excel format |
| --- | --- | --- | --- |
| ZA | [za/CURLS.md](./za/CURLS.md) | [za/response.md](./za/response.md) | [za/EXCEL_REPORT.md](./za/EXCEL_REPORT.md) |
| GLO DE | [glo-de/CURLS.md](./glo-de/CURLS.md) | [glo-de/response.md](./glo-de/response.md) | [glo-de/EXCEL_REPORT.md](./glo-de/EXCEL_REPORT.md) |
| GLO PL | [glo-pl/CURLS.md](./glo-pl/CURLS.md) | [glo-pl/response.md](./glo-pl/response.md) | [glo-pl/EXCEL_REPORT.md](./glo-pl/EXCEL_REPORT.md) |
| Japan | [japan/CURLS.md](./japan/CURLS.md) | [japan/response.md](./japan/response.md) | [japan/EXCEL_REPORT.md](./japan/EXCEL_REPORT.md) |
| Korea | [korea/CURLS.md](./korea/CURLS.md) | [korea/response.md](./korea/response.md) | [korea/EXCEL_REPORT.md](./korea/EXCEL_REPORT.md) |
| B2B KR | [b2b-kr/CURLS.md](./b2b-kr/CURLS.md) | [b2b-kr/response.md](./b2b-kr/response.md) | [b2b-kr/EXCEL_REPORT.md](./b2b-kr/EXCEL_REPORT.md) |
| VELO PL | [velo-pl/CURLS.md](./velo-pl/CURLS.md) | [velo-pl/response.md](./velo-pl/response.md) | [velo-pl/EXCEL_REPORT.md](./velo-pl/EXCEL_REPORT.md) |
| VUSE DE | [vuse-de/CURLS.md](./vuse-de/CURLS.md) | [vuse-de/response.md](./vuse-de/response.md) | [vuse-de/EXCEL_REPORT.md](./vuse-de/EXCEL_REPORT.md) |
| GLO IT | [glo-it/CURLS.md](./glo-it/CURLS.md) | [glo-it/response.md](./glo-it/response.md) | [glo-it/EXCEL_REPORT.md](./glo-it/EXCEL_REPORT.md) |
| Serbia | [serbia/CURLS.md](./serbia/CURLS.md) | [serbia/response.md](./serbia/response.md) | [serbia/EXCEL_REPORT.md](./serbia/EXCEL_REPORT.md) |
| VELO IT | [velo-it/CURLS.md](./velo-it/CURLS.md) | [velo-it/response.md](./velo-it/response.md) | [velo-it/EXCEL_REPORT.md](./velo-it/EXCEL_REPORT.md) |
| VUSE IT | [vuse-it/CURLS.md](./vuse-it/CURLS.md) | [vuse-it/response.md](./vuse-it/response.md) | [vuse-it/EXCEL_REPORT.md](./vuse-it/EXCEL_REPORT.md) |
| Tetris FR | [tetris-fr/CURLS.md](./tetris-fr/CURLS.md) | [tetris-fr/response.md](./tetris-fr/response.md) | [tetris-fr/EXCEL_REPORT.md](./tetris-fr/EXCEL_REPORT.md) |
| Tetris GR | [tetris-gr/CURLS.md](./tetris-gr/CURLS.md) | [tetris-gr/response.md](./tetris-gr/response.md) | [tetris-gr/EXCEL_REPORT.md](./tetris-gr/EXCEL_REPORT.md) |

Tetris FR and Tetris GR use the `TETRIS_API_KEY` GitHub Actions secret; all other markets use `NEW_RELIC_API_KEY`. Add both secrets under **Settings → Secrets and variables → Actions**. Secret names cannot contain spaces.
