```powershell
curl.exe --request POST `
  --url "https://api.newrelic.com/graphql" `
  --header "API-Key: $env:NEW_RELIC_API_KEY" `
  --header "Content-Type: application/json" `
  --data-raw '{"query":"query DashboardMetrics($nrql: String!) { actor { normalOrderCreation: account(id: 6538703) { nrql(query: $nrql) { results } } } }","variables":{"nrql":"FROM Log SELECT count(*) SINCE 24 hours ago"}}'
```
