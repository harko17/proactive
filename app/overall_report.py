from __future__ import annotations

import re
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.market import _match_score


OVERALL_REPORT_TITLE = "Overall Market Monitoring Report"
MARKET_COLUMNS = {
    "ZA": "za",
    "GLO DE": "glo-de",
    "GLO PL": "glo-pl",
    "Japan": "japan",
    "Korea": "korea",
    "B2B KR": "b2b-kr",
    "VELO PL": "velo-pl",
    "VUSE DE": "vuse-de",
    "GLO IT": "glo-it",
    "Serbia": "serbia",
    "VELO IT": "velo-it",
    "VUSE IT": "vuse-it",
    "Tetris FR": "tetris-fr",
    "Tetris GR": "tetris-gr",
}


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _metric_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _read_template(path: Path) -> tuple[list[str], list[list[str]]]:
    table_rows = [_cells(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip().startswith("|")]
    if not table_rows:
        raise ValueError(f"No Markdown table found in overall report template: {path}")

    headers = table_rows[0]
    expected_headers = ["Areas", *MARKET_COLUMNS]
    if headers != expected_headers:
        raise ValueError(
            f"Overall report headers in {path} must be {expected_headers!r}; found {headers!r}"
        )

    metric_rows = [row for row in table_rows[1:] if len(row) == len(headers) and row[0]]
    if not metric_rows:
        raise ValueError(f"No metric rows found in overall report template: {path}")
    return headers, metric_rows


def _read_market_values(path: Path) -> list[tuple[str, object]]:
    if not path.is_file():
        raise FileNotFoundError(f"Market report workbook is missing: {path}")
    workbook = load_workbook(path, data_only=True, read_only=True)
    try:
        if "Dashboard Summary" not in workbook.sheetnames:
            raise ValueError(f"Market report workbook has no Dashboard Summary sheet: {path}")
        sheet = workbook["Dashboard Summary"]
        return [
            (str(row[1]).strip(), row[3])
            for row in sheet.iter_rows(min_row=2, values_only=True)
            if len(row) >= 4 and row[1] is not None and str(row[1]).strip()
        ]
    finally:
        workbook.close()


def _format_value(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return format(value, ".15g")
    return str(value).strip() or "-"


def _find_value(metric: str, report_rows: list[tuple[str, object]]) -> str:
    normalized_metric = _metric_key(metric)
    exact_matches = [value for label, value in report_rows if _metric_key(label) == normalized_metric]
    if exact_matches:
        return _format_value(exact_matches[0])

    matches = sorted(
        ((_match_score(label, metric), label, value) for label, value in report_rows),
        key=lambda match: (match[0], match[1]),
        reverse=True,
    )
    if not matches or matches[0][0] < 0.9:
        return "-"
    if len(matches) > 1 and matches[0][0] - matches[1][0] < 0.06:
        return "-"
    return _format_value(matches[0][2])


def generate_overall_report(template_path: Path, reports_dir: Path, output_path: Path) -> str:
    headers, metric_rows = _read_template(template_path)
    values_by_market = {
        market: _read_market_values(reports_dir / f"{slug}.xlsx")
        for market, slug in MARKET_COLUMNS.items()
    }

    report_rows = []
    for template_row in metric_rows:
        metric = template_row[0]
        report_rows.append([
            metric,
            *[
                _find_value(metric, values_by_market[market])
                for market in MARKET_COLUMNS
            ],
        ])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Overall Summary"
    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
    title = sheet.cell(row=1, column=1, value=OVERALL_REPORT_TITLE)
    title.font = Font(name="Aptos", size=14, bold=True, color="FFFFFF")
    title.fill = PatternFill("solid", fgColor="477C7D")
    title.alignment = Alignment(horizontal="center", vertical="center")
    sheet.row_dimensions[1].height = 26

    thin_gray = Side(style="thin", color="B7C9C9")
    grid_border = Border(left=thin_gray, right=thin_gray, top=thin_gray, bottom=thin_gray)
    for column, header in enumerate(headers, start=1):
        cell = sheet.cell(row=2, column=column, value=header)
        cell.font = Font(name="Aptos", size=11, bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="5B9A9B")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = grid_border
    sheet.row_dimensions[2].height = 30

    for row_index, row in enumerate(report_rows, start=3):
        for column, value in enumerate(row, start=1):
            cell_value = value
            if column > 1 and value != "-":
                try:
                    cell_value = float(value) if "." in value else int(value)
                except ValueError:
                    pass
            cell = sheet.cell(row=row_index, column=column, value=cell_value)
            cell.font = Font(name="Aptos", size=10, color="263238")
            cell.alignment = Alignment(
                horizontal="left" if column == 1 else "center",
                vertical="center",
            )
            cell.border = grid_border
            if row_index % 2 == 1:
                cell.fill = PatternFill("solid", fgColor="EAF2F2")

    sheet.column_dimensions["A"].width = 58
    for column in range(2, len(headers) + 1):
        sheet.column_dimensions[get_column_letter(column)].width = 14
    sheet.freeze_panes = "B3"
    sheet.auto_filter.ref = f"A2:{get_column_letter(len(headers))}{len(report_rows) + 2}"
    sheet.sheet_view.showGridLines = False
    workbook.save(output_path)
    return str(output_path)
