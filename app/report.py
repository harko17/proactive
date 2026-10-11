from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


class ExcelReportWriter:
    def __init__(self, output_path: str):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, rows: list[dict]) -> str:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Dashboard Summary"

        dashboard_name = next((row.get("dashboard_name") for row in rows if row.get("dashboard_name")), "New Relic Dashboard")
        dashboard_url = next((row.get("dashboard_url") for row in rows if row.get("dashboard_url")), "")
        sheet.merge_cells("A1:B1")
        title_cell = sheet.cell(row=1, column=1, value=f"{dashboard_name} - Monitoring charts")
        title_cell.font = Font(name="Aptos", size=12, bold=True, color="477C7D", underline="single")
        title_cell.fill = PatternFill("solid", fgColor="A9CBE8")
        title_cell.alignment = Alignment(horizontal="center", vertical="center")
        if dashboard_url.lower().startswith(("https://", "http://")):
            title_cell.hyperlink = dashboard_url
        monitor_cell = sheet.cell(row=1, column=3, value="Monitoring")
        monitor_cell.font = Font(name="Aptos", size=12, bold=True)
        monitor_cell.fill = PatternFill("solid", fgColor="A9CBE8")
        monitor_cell.alignment = Alignment(horizontal="left", vertical="center")
        sheet.cell(row=1, column=4).fill = PatternFill("solid", fgColor="A9CBE8")
        sheet.row_dimensions[1].height = 22

        thin_black = Side(style="thin", color="000000")
        grid_border = Border(left=thin_black, right=thin_black, top=thin_black, bottom=thin_black)
        for row_index, row in enumerate(rows, start=2):
            values = [
                row.get("category", ""),
                row.get("metric_name", ""),
                row.get("metric_type", ""),
                self._excel_value(row.get("value")),
            ]
            for column, value in enumerate(values, start=1):
                cell = sheet.cell(row=row_index, column=column, value=value)
                cell.border = grid_border
                cell.font = Font(name="Aptos", size=11, color="263238")
                cell.alignment = Alignment(
                    horizontal="right" if column == 4 else ("center" if column == 1 else "left"),
                    vertical="center",
                )
            sheet.row_dimensions[row_index].height = 22

        category_start = 0
        while category_start < len(rows):
            category = rows[category_start].get("category", "")
            category_end = category_start + 1
            while category_end < len(rows) and rows[category_end].get("category", "") == category:
                category_end += 1
            excel_start = category_start + 2
            excel_end = category_end + 1
            if category_end - category_start > 1:
                sheet.merge_cells(start_row=excel_start, start_column=1, end_row=excel_end, end_column=1)
                category_cell = sheet.cell(row=excel_start, column=1)
                category_cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                category_cell.border = grid_border
            category_start = category_end

        for column, width in enumerate([54, 73, 18, 14], start=1):
            sheet.column_dimensions[get_column_letter(column)].width = width
        sheet.freeze_panes = "B2"
        sheet.sheet_view.showGridLines = False
        workbook.save(self.output_path)
        return str(self.output_path)

    @staticmethod
    def _excel_value(value):
        if isinstance(value, bool) or value is None:
            return value
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            try:
                return float(value) if "." in value else int(value)
            except ValueError:
                return value
        return str(value)
