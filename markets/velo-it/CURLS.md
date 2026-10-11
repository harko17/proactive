# VELO IT NerdGraph request

The cURL command and headers are shared across markets. Replace only the JSON request body below with this market's complete Postman `--data-raw` body. Do not include an API key in the file.

```powershell
$body = @'
{
  "query": "query {\n  actor {\n    normalOrderCreation: nrql(accounts: [6358718], query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%VeloIT-order-count%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n    pendingProcessingStatus: nrql(accounts: [6358718], query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%VeloIT-processing-pending-order-count%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n    pendingPayment: nrql(accounts: [6358718], query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%VeloIT-pending_payment-order-count%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n    customerCreationSyncToCRMTrend: nrql(accounts: [6358718], query: \"FROM Log SELECT filter(count(*), WHERE `filePath` = '/data/exports/local/liytwnjfn7kgg/log/customer_crm_syn.log' AND `message` LIKE '%source\\\\\\\\\\\":\\\\\\\\\\\"eCommerce - Velo%' AND `message` LIKE '%customer_create%' AND `message` LIKE '%Customer API Request and Response%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n    orderCreationSyncToCRMTrend: nrql(accounts: [6358718], query: \"FROM Log SELECT filter(count(*), WHERE `filePath` = '/data/exports/local/liytwnjfn7kgg/log/salesforce_order.log' AND `message` LIKE '%IT-Velo-%' AND `message` LIKE '%Order API Request and Response%' AND `message` LIKE '%countryCode\\\\\\\\\\\":\\\\\\\\\\\"IT%' AND `message` LIKE '%order_create%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n    customerWithoutSFID: nrql(accounts: [6358718], query: \"SELECT count(*)  FROM Log WHERE `message` LIKE '%VeloIT-customer-without SF id%' SINCE 24 HOURS AGO TIMESERIES\") { results }\n    ageUnverifiedCustomerOrderCount: nrql(accounts: [6358718], query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%VeloIT-Age-Unverified-Customer-order-Count%') SINCE 24 HOURS AGO\") { results }\n    accountConfirmationEmail: nrql(accounts: [6358718], query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%VeloIT-account-confirmation-email-count%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n    orderConfirmationEmail: nrql(accounts: [6358718], query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%VeloIT-order-confirmation-email-count%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n    shipmentConfirmationEmail: nrql(accounts: [6358718], query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%VeloIT-shipment-confirmation-email-count%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n  }\n}"
}
'@

curl.exe --request POST `
  --url "https://api.newrelic.com/graphql" `
  --header "API-Key: $env:NEW_RELIC_API_KEY" `
  --header "Content-Type: application/json" `
  --data-raw $body
```
