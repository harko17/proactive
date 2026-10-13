# Tetris GR NerdGraph request

This market's complete GraphQL request contains the GR monitoring queries and uses New Relic account `4539838`.

Do not include an API key in this file. The eventual GitHub Actions secret is `TETRIS_API_KEY`.

```powershell
$body = @'
{
  "query": "query {\n  actor {\n    account(id: 4539838) {\n      stuckInPendingStatus: nrql(query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%GRB2B-pending-order-count%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n      stuckInProcessingStatus: nrql(query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%GRB2B-processing-order-count%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n      stuckInDistributorUnavailable: nrql(query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%GRB2B-distributor-unavailable-order-count%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n      closedOrders: nrql(query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%GRB2B-closed-order-count%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n      inventoryMonitorInventoryUpdateFailure: nrql(query: \"FROM Log SELECT count(*) WHERE allColumnSearch('POST /rest/tetris_gr_el_gr/V1/inventory/source-items HTTP/1.1\\\" 400', insensitive: true) SINCE 24 HOURS AGO\") { results }\n      productMonitorNewSkuFound: nrql(query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%GRB2B-new-product-found%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n      productMonitorSkuWithHyphenFound: nrql(query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%GRB2B-sku-hyphen-found%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n      companyPendingApprovalCompanyNotActive: nrql(query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%GRB2B-company-not-active-count%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n      duplicatePosCode: nrql(query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%GRB2B-duplicate-pos-code-count%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n      duplicateOlIds: nrql(query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%GRB2B-duplicate-OL-IDs%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n      addressVerificationDotAddressInSecondLine: nrql(query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%GRB2B-dot-address-found%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n      inventorySourceInventorySourceNotAssignedForOutlets: nrql(query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%GRB2B-company-no-inventory-source%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n    }\n  }\n}"
}
'@

curl.exe --request POST `
  --url "https://api.newrelic.com/graphql" `
  --header "API-Key: $env:TETRIS_API_KEY" `
  --header "Content-Type: application/json" `
  --data-raw $body
```
