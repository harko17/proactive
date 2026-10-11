# Serbia NerdGraph request

The cURL command and headers are shared across markets. Replace only the JSON request body below with this market's complete Postman `--data-raw` body. Do not include an API key in the file.

```powershell
$body = @'
{
  "query": "PASTE_MARKET_SPECIFIC_GRAPHQL_QUERY_HERE"
}
'@

curl.exe --request POST `
  --url "https://api.newrelic.com/graphql" `
  --header "API-Key: $env:NEW_RELIC_API_KEY" `
  --header "Content-Type: application/json" `
  --data-raw $body
```
