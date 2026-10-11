from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path


_TOKEN_RE = re.compile(
    r'"(?:\\.|[^"\\])*"|[_A-Za-z][_0-9A-Za-z]*|-?\d+|[!$():=@\[\]{},]'
)
_VERTICALS_RE = re.compile(r"[|\u2502\u2551]")
_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

_JAPAN_LAYOUT = [
    ("Order Creation", "Normal Order Creation", "count"),
    ("Order Creation", "Awaiting Capture / Payment review", "latest value"),
    ("Order Creation", "Pending / Processing status", "latest value"),
    ("Order Creation", "Awaiting shipment", "latest value"),
    ("Order Fulfillment", "Shipment instruction Cron Error monitor", "count"),
    ("Order Fulfillment", "Pending Payment Cancellations", "count"),
    ("Order Fulfillment", "JP Order Shipped Status", "trend"),
    ("Order Fulfillment", "Orders yet to sync downstream", "latest value"),
    ("Order Fulfillment", "Shipment result processing monitor", "trend"),
    ("Order Fulfillment", "Shipment instruction Cron monitor", "trend"),
    ("Order Fulfillment", "Order Status Import Error Monitor", "count"),
    ("Order Fulfillment", "Shipment result processing error monitor", "count"),
    ("Order Fulfillment", "Device Trial Payment Pending Charge", "trend"),
    ("Integration", "Customer creation sync to CRM - Trend", "trend"),
    ("Integration", "Customer Sync to Magento - Error", "count"),
    ("Integration", "Abandoned Cart Update Error", "count"),
    ("Integration", "Product Update Error", "count"),
    ("Integration", "Back in Stock Notification Error", "count"),
    ("Integration", "Order create event - Trend", "trend"),
    ("Integration", "Customer creation/update Error", "count"),
    ("Integration", "Order create/update event error", "count"),
    ("Integration", "Award Coupon API failure", "count"),
    ("Integration", "SiteCore API failure", "count"),
    ("Integration", "Award Badge API failure", "count"),
    ("Integration", "Award Points API failure", "count"),
    ("Integration", "Product Update Pricebook error", "count"),
    ("Integration", "Sagawa Express API Error", "count"),
    ("Integration", "Stock Process File Monitor", "trend"),
    ("Integration", "Customer creation yet to sync Sitecore/CRM", "latest value"),
    ("Integration", "Orders yet to sync downstream (time series)", "trend"),
    ("Transactional Email and Inventory", "Order confirmation email", "trend"),
    ("Transactional Email and Inventory", "Shipment confirmation email", "trend"),
    ("Age Verification/Account Confirmation", "Age unverified customer order count", "latest value"),
    ("Integration", "Docomo outbound API call", "count"),
]


def load_request(curl_path: Path) -> tuple[dict, list[dict]]:
    document = curl_path.read_text(encoding="utf-8")
    body_match = re.search(r"\$body\s*=\s*@'\s*\r?\n([\s\S]*?)\r?\n'@", document)
    if not body_match:
        raise ValueError(f"Could not find the --data-raw JSON body in {curl_path}")

    payload = json.loads(body_match.group(1))
    if not isinstance(payload, dict) or not isinstance(payload.get("query"), str):
        raise ValueError(f"The cURL request body in {curl_path} must contain a GraphQL query")

    entries = parse_graphql_entries(payload["query"])
    if not entries:
        raise ValueError(f"No aliased NRQL queries were found in {curl_path}")
    aliases = [entry["alias"] for entry in entries]
    if len(aliases) != len(set(aliases)):
        raise ValueError(f"Duplicate GraphQL aliases were found in {curl_path}")
    return payload, entries


def _parse_value(tokens: list[str], index: int):
    token = tokens[index]
    if token.startswith('"'):
        return json.loads(token), index + 1
    if token == "[":
        values = []
        index += 1
        while index < len(tokens) and tokens[index] != "]":
            if tokens[index] == ",":
                index += 1
                continue
            value, index = _parse_value(tokens, index)
            values.append(value)
        if index >= len(tokens):
            raise ValueError("Unclosed list in GraphQL arguments")
        return values, index + 1
    if re.fullmatch(r"-?\d+", token):
        return int(token), index + 1
    if token in {"true", "false", "null"}:
        return {"true": True, "false": False, "null": None}[token], index + 1
    return token, index + 1


def _parse_arguments(tokens: list[str], index: int) -> tuple[dict, int]:
    arguments = {}
    while index < len(tokens) and tokens[index] != ")":
        if tokens[index] == ",":
            index += 1
            continue
        name = tokens[index]
        index += 1
        if index >= len(tokens) or tokens[index] != ":":
            raise ValueError(f"Invalid GraphQL argument near {name!r}")
        value, index = _parse_value(tokens, index + 1)
        arguments[name] = value
    if index >= len(tokens):
        raise ValueError("Unclosed GraphQL argument list")
    return arguments, index + 1


def _parse_selection_set(
    tokens: list[str],
    index: int,
    entries: list[dict],
    inherited_alias: str | None = None,
    inherited_account_id: str | None = None,
) -> int:
    while index < len(tokens) and tokens[index] != "}":
        if tokens[index] == ",":
            index += 1
            continue
        if tokens[index] == "@":
            index += 2
            if index < len(tokens) and tokens[index] == "(":
                _, index = _parse_arguments(tokens, index + 1)
            continue

        first_name = tokens[index]
        index += 1
        alias = None
        if index < len(tokens) and tokens[index] == ":":
            alias = first_name
            index += 1
            field_name = tokens[index]
            index += 1
        else:
            field_name = first_name

        arguments = {}
        if index < len(tokens) and tokens[index] == "(":
            arguments, index = _parse_arguments(tokens, index + 1)

        current_alias = alias or inherited_alias
        current_account_id = inherited_account_id
        if field_name == "account":
            account_id = arguments.get("id")
            if isinstance(account_id, int) and account_id > 0:
                current_account_id = str(account_id)
            elif account_id is not None:
                raise ValueError(f"Invalid New Relic account ID {account_id!r}")
        elif field_name == "nrql":
            account_ids = arguments.get("accounts")
            if isinstance(account_ids, list) and account_ids:
                account_id = account_ids[0]
                if isinstance(account_id, int) and account_id > 0:
                    current_account_id = str(account_id)
                else:
                    raise ValueError(f"Invalid New Relic account ID {account_id!r}")
            query = arguments.get("query")
            if current_alias and isinstance(query, str) and current_account_id:
                entries.append({
                    "alias": current_alias,
                    "account_id": current_account_id,
                    "query": query,
                })

        if index < len(tokens) and tokens[index] == "{":
            index = _parse_selection_set(
                tokens,
                index + 1,
                entries,
                current_alias,
                current_account_id,
            )
        if index < len(tokens) and tokens[index] == "}":
            break

    if index >= len(tokens):
        raise ValueError("Unclosed GraphQL selection set")
    return index + 1


def parse_graphql_entries(graphql_query: str) -> list[dict]:
    tokens = _TOKEN_RE.findall(graphql_query)
    entries = []
    for index, token in enumerate(tokens[:-1]):
        if token == "actor" and tokens[index + 1] == "{":
            _parse_selection_set(tokens, index + 2, entries)
            break
    return entries


def parse_report_layout(spec_path: Path, market_slug: str) -> dict:
    document = spec_path.read_text(encoding="utf-8")
    example_index = document.lower().find("example layout")
    example = document[example_index + len("example layout"):] if example_index >= 0 else ""

    title = market_slug.replace("-", " ").title()
    title_column = 1
    rows = []
    category = ""
    repeated_categories = False
    seen_categories = set()

    for line in example.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("|") or stripped.startswith("\u2502") or stripped.startswith("\u2551")):
            continue
        columns = [cell.strip() for cell in _VERTICALS_RE.split(stripped)[1:-1]]
        if len(columns) < 4:
            continue
        columns = columns[:4]
        title_cell_index = next(
            (index for index, cell in enumerate(columns) if "monitoring charts" in cell.lower()),
            None,
        )
        if title_cell_index is not None:
            title_column = title_cell_index + 1
            title = re.sub(r"\s*-\s*Monitoring charts\s*$", "", columns[title_cell_index], flags=re.IGNORECASE)
            title = title.strip() or market_slug.replace("-", " ").title()
            continue

        name = columns[1]
        metric_type = columns[2]
        if not name or name.isspace():
            continue
        if not metric_type and not columns[3] and rows:
            rows[-1]["metric_name"] = f"{rows[-1]['metric_name']} {name}".strip()
            continue

        row_category = columns[0]
        if row_category:
            repeated_categories = repeated_categories or row_category in seen_categories
            seen_categories.add(row_category)
            category = row_category
        if category:
            rows.append({
                "category": category,
                "metric_name": name,
                "metric_type": metric_type,
            })

    if not rows and market_slug == "japan":
        rows = [
            {"category": category, "metric_name": name, "metric_type": metric_type}
            for category, name, metric_type in _JAPAN_LAYOUT
        ]

    return {
        "title": title,
        "title_column": title_column,
        "rows": rows,
        "merge_categories": not repeated_categories,
    }


def _normalized_words(value: str) -> list[str]:
    separated = _CAMEL_BOUNDARY_RE.sub(" ", value)
    return re.findall(r"[a-z0-9]+", separated.lower())


def _match_score(alias: str, metric_name: str) -> float:
    alias_words = _normalized_words(alias)
    label_words = _normalized_words(metric_name)
    alias_text = " ".join(alias_words)
    label_text = " ".join(label_words)
    sequence_score = SequenceMatcher(None, alias_text, label_text).ratio()
    alias_set, label_set = set(alias_words), set(label_words)
    token_score = len(alias_set & label_set) / max(len(alias_set | label_set), 1)
    return max(sequence_score, token_score)


def apply_report_layout(entries: list[dict], layout: dict) -> list[dict]:
    available = list(entries)
    report_rows = []

    for layout_row in layout["rows"]:
        best_entry = None
        best_score = 0.0
        for entry in available:
            score = _match_score(entry["alias"], layout_row["metric_name"])
            alias_words = set(_normalized_words(entry["alias"]))
            if layout_row["metric_type"].lower() == "trend":
                if "trend" in alias_words:
                    score += 0.16
                if alias_words & {"error", "failure", "failed"}:
                    score -= 0.12
            if score > best_score:
                best_entry, best_score = entry, score

        if best_entry is not None and best_score >= 0.32:
            available.remove(best_entry)
            report_rows.append({
                **best_entry,
                **layout_row,
                "mapping_status": "matched",
            })
        else:
            report_rows.append({
                **layout_row,
                "alias": None,
                "account_id": "",
                "query": "",
                "mapping_status": "layout row has no matching query",
            })

    for entry in available:
        alias_words = _normalized_words(entry["alias"])
        alias_name = " ".join(word.capitalize() for word in alias_words)
        report_rows.append({
            **entry,
            "category": _fallback_category(alias_words),
            "metric_name": alias_name,
            "metric_type": "trend" if "timeseries" in entry["query"].lower() else "count",
            "mapping_status": "query is not in the layout example",
        })
    return report_rows


def _fallback_category(alias_words: list[str]) -> str:
    alias = " ".join(alias_words)
    if "email" in alias or "invoice" in alias:
        return "Transactional Email"
    if "age" in alias or "yoti" in alias:
        return "Age Verification/Account Confirmation"
    if any(word in alias for word in ("shipment", "order", "payment", "fulfilment", "fulfillment")):
        return "Order Fulfillment"
    return "Additional Integration"
