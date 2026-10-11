# VUSE IT NerdGraph request

The cURL command and headers are shared across markets. Replace only the JSON request body below with this market's complete Postman `--data-raw` body. Do not include an API key in the file.

```powershell
$body = @'
{
  "query": "query {\n  actor {\n    normalOrderCreation: nrql(accounts: [6358718], query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%Vuse-IT-order-count%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n    pendingProcessingStatus: nrql(accounts: [6358718], query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%Vuse-IT-processing-pending-order-count%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n    pendingPayment: nrql(accounts: [6358718], query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%Vuse-IT-pending_payment-order-count%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n    orderFulfillmentOrderExport: nrql(accounts: [6358718], query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%Export is done. location - %var/shipment_process/export/vuse%' AND `filePath` = '/data/exports/local/liytwnjfn7kgg/log/support_report.log') SINCE 24 HOURS AGO TIMESERIES\") { results }\n    customerCreationSyncToCrmTrend: nrql(accounts: [6358718], query: \"FROM Log SELECT filter(count(*), WHERE `filePath` = '/data/exports/local/liytwnjfn7kgg/log/customer_crm_syn.log' AND `message` LIKE '%source\\\\\\\\\\\":\\\\\\\\\\\"eCommerce - Vuse%' AND `message` LIKE '%customer_create%' AND `message` LIKE '%Customer API Request and Response%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n    orderCreationToCrmTrend: nrql(accounts: [6358718], query: \"FROM Log SELECT filter(count(*), WHERE `filePath` = '/data/exports/local/liytwnjfn7kgg/log/salesforce_order.log' AND `message` LIKE '%IT-Vuse-%' AND `message` LIKE '%Order API Request and Response%' AND `message` LIKE '%order_create%' AND `message` LIKE '%countryCode\\\\\\\\\\\":\\\\\\\\\\\"IT%' ) SINCE 24 HOURS AGO TIMESERIES\") { results }\n    customerWithoutSfId: nrql(accounts: [6358718], query: \"SELECT count(*)  FROM Log WHERE `message` LIKE '%VuseIT-customer-without SF id%' SINCE 24 HOURS AGO TIMESERIES\") { results }\n    accountConfirmationEmail: nrql(accounts: [6358718], query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%VuseIT-account-confirmation-email-count%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n    orderConfirmationEmail: nrql(accounts: [6358718], query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%Vuse-IT-order-confirmation-email-count%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n    shipmentConfirmationEmail: nrql(accounts: [6358718], query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%Vuse-IT-shipment-confirmation-email-count%') SINCE 24 HOURS AGO TIMESERIES\") { results }\n    ageUnverifiedCustomerOrderCount: nrql(accounts: [6358718], query: \"FROM Log SELECT filter(count(*), WHERE `message` LIKE '%Vuse-IT-Age-Unverified-Customer-order-Count%') SINCE 24 HOURS AGO\") { results }\n  }\n}"
}
'@

curl.exe --request POST `
  --url "https://api.newrelic.com/graphql" `
  --header "API-Key: $env:NEW_RELIC_API_KEY" `
  --header "Content-Type: application/json" `
  --data-raw $body
```
