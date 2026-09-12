"""Builds the downloadable self-assessment PDF from an already-computed tax result.

Uses reportlab (pure-Python, no system library dependency) rather than an HTML->PDF
tool like weasyprint — avoids Pango/Cairo install pain on Windows dev machines and on
Render's free tier.
"""
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from modules.tax_computation.engine import TaxComputationResult


def _format_period(period_start: datetime | None, period_end: datetime | None) -> str:
    if period_start is None or period_end is None:
        return "No approved records for this tax year yet"
    if period_start.date() == period_end.date():
        return period_start.strftime("%d %b %Y")
    return f"{period_start.strftime('%d %b %Y')} – {period_end.strftime('%d %b %Y')}"


def build_report_pdf(
    user_name: str,
    tax_year: str,
    result: TaxComputationResult,
    items: dict | None = None,
    *,
    tin: str | None = None,
    state_residence: str | None = None,
    occupation_type: str | None = None,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> bytes:
    """`items` is the same {income_items, deduction_items, capital_allowance_items,
    relief_items} shape the web Reports page renders (see
    modules/tax_computation/reporting_helpers.py) — optional so any existing caller
    that doesn't have it yet still gets a valid PDF, just without the itemization.

    `period_start`/`period_end` are the earliest/latest APPROVED record dates
    actually on file for the year (see loader.get_records_period) — deliberately
    not just "Jan 1 - Dec 31 of tax_year", so a user with a partial year of records
    sees that reflected honestly rather than implying full-year coverage.
    """
    items = items or {}
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"GigTax Self-Assessment Report — {tax_year}", styles["Title"]),
        Paragraph(f"Prepared for: {user_name}", styles["Normal"]),
        Paragraph(f"TIN: {tin or 'Not provided'}", styles["Normal"]),
        Paragraph(f"State of Residence: {state_residence or 'Not provided'}", styles["Normal"]),
        Paragraph(f"Occupation: {occupation_type or 'Not provided'}", styles["Normal"]),
        Paragraph(f"Records Covered: {_format_period(period_start, period_end)}", styles["Normal"]),
        Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]),
        Spacer(1, 0.5 * cm),
    ]

    if result.minimum_wage_exempt:
        story.append(Paragraph(
            "Total income is at or below the National Minimum Wage — fully exempt under "
            "NTA 2025 s.58 / s.162(1)(t). No further computation applies.",
            styles["Normal"],
        ))
    else:
        summary_data = [
            ["Total Income (NTA 2025 s.28)", f"₦{result.total_income:,.2f}"],
            ["Allowable Deductions (ss.20-21)", f"₦{result.total_deductions:,.2f}"],
            ["Capital Allowances (First Schedule)", f"₦{result.total_capital_allowances:,.2f}"],
            ["Statutory Reliefs (s.30)", f"₦{result.total_reliefs:,.2f}"],
            ["Chargeable Income", f"₦{result.chargeable_income:,.2f}"],
            ["Net Tax Payable (Fourth Schedule, s.58)", f"₦{result.net_tax:,.2f}"],
        ]
        summary_table = Table(summary_data, colWidths=[9 * cm, 6 * cm])
        summary_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.5 * cm))

        item_sections = [
            ("Income", items.get("income_items", [])),
            ("Allowable Deductions", items.get("deduction_items", [])),
            ("Capital Allowances", items.get("capital_allowance_items", [])),
            ("Statutory Reliefs", items.get("relief_items", [])),
        ]
        if any(entries for _, entries in item_sections):
            story.append(Paragraph("Itemized Breakdown", styles["Heading2"]))
            for section_label, entries in item_sections:
                if not entries:
                    continue
                story.append(Paragraph(section_label, styles["Heading3"]))
                # Deduction and capital allowance items carry `rate`/`gross_amount`
                # (see reporting_helpers.build_itemized_breakdown and
                # loader.load_capital_allowance_items) — shown as their own columns
                # so a reader can see, e.g., "100%" for a normal expense versus a
                # home-office category's user-set percentage, and the original
                # amount that rate was applied to.
                has_rate = any(entry.get("rate") is not None for entry in entries)
                if has_rate:
                    item_data = [["Category", "Gross Amount", "Rate", "Amount Deducted"]] + [
                        [
                            entry["category_name"],
                            f"₦{entry.get('gross_amount', entry['amount']):,.2f}",
                            f"{entry['rate']:.0f}%",
                            f"₦{entry['amount']:,.2f}",
                        ]
                        for entry in entries
                    ]
                    col_widths = [6.5 * cm, 4 * cm, 2 * cm, 4 * cm]
                else:
                    item_data = [["Category", "Amount"]] + [
                        [entry["category_name"], f"₦{entry['amount']:,.2f}"] for entry in entries
                    ]
                    col_widths = [9 * cm, 6 * cm]
                item_table = Table(item_data, colWidths=col_widths)
                item_table.setStyle(TableStyle([
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ]))
                story.append(item_table)
                story.append(Spacer(1, 0.3 * cm))

        story.append(Paragraph("Band-by-band computation (Fourth Schedule)", styles["Heading2"]))
        band_data = [["Rate", "Amount in Band", "Tax"]]
        for band in result.band_breakdown:
            band_data.append([f"{band.rate * 100:.0f}%", f"₦{band.amount_in_band:,.2f}", f"₦{band.tax:,.2f}"])
        band_table = Table(band_data, colWidths=[3 * cm, 6 * cm, 6 * cm])
        band_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ]))
        story.append(band_table)

    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(
        "This is a self-assessment estimate generated by GigTax based on the transactions you "
        "reviewed and approved. It is not a substitute for professional tax advice.",
        styles["Italic"],
    ))

    doc.build(story)
    return buffer.getvalue()
