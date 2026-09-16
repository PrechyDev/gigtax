"""Builds the downloadable self-assessment PDF from an already-computed tax result.

Uses reportlab (pure-Python, no system library dependency) rather than an HTML->PDF
tool like weasyprint — avoids Pango/Cairo install pain on Windows dev machines and on
Render's free tier.

Visual language mirrors the web app's own tokens (frontend/src/index.css's light-mode
`--color-navy`/`--color-accent`/etc.) rather than reportlab's plain default styling, so
the PDF reads as the same product as the Reports page it's downloaded from. Text uses
DejaVu Sans (bundled here under `fonts/`, Bitstream Vera-derived license in
`fonts/LICENSE` — free to redistribute) instead of reportlab's built-in Helvetica/Times,
because none of the 14 standard PDF fonts contain a Naira sign (U+20A6) glyph; without
a real Unicode font it renders as a blank box in every PDF viewer.
"""
import io
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from modules.tax_computation.engine import TaxComputationResult

# --- Brand -----------------------------------------------------------------
# Same hues as the app's light-mode CSS tokens (index.css) — the PDF has no dark
# mode of its own (paper is always "light"), so these are the light-mode values.
NAVY = colors.HexColor("#17181a")       # --color-navy / --color-on-surface
ACCENT = colors.HexColor("#416180")     # --color-accent
ACCENT_DARK = colors.HexColor("#2c455d")  # --color-accent-dark
ACCENT_TINT = colors.HexColor("#e8edf1")  # a light tint of --color-accent for header fills
MUTED = colors.HexColor("#4a4d50")      # --color-on-surface-variant
DIVIDER = colors.HexColor("#cdd0d3")    # --color-outline-variant
EXEMPT_GREEN = colors.HexColor("#1b7a43")
EXEMPT_TINT = colors.HexColor("#e9f7ee")

PAGE_WIDTH, PAGE_HEIGHT = A4
CONTENT_WIDTH = PAGE_WIDTH - 4 * cm  # matches the 2cm left/right margins below

_FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
_FONTS_REGISTERED = False


def _register_fonts() -> None:
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    pdfmetrics.registerFont(TTFont("GigTaxSans", os.path.join(_FONT_DIR, "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("GigTaxSans-Bold", os.path.join(_FONT_DIR, "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("GigTaxSans-Oblique", os.path.join(_FONT_DIR, "DejaVuSans-Oblique.ttf")))
    registerFontFamily(
        "GigTaxSans",
        normal="GigTaxSans",
        bold="GigTaxSans-Bold",
        italic="GigTaxSans-Oblique",
        boldItalic="GigTaxSans-Bold",
    )
    _FONTS_REGISTERED = True


def _styles() -> dict:
    """Extends reportlab's sample stylesheet with GigTax-branded variants (its own
    'Title'/'Heading2'/etc. use the un-Unicode Helvetica and have no brand color)."""
    _register_fonts()
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle(name="GTBrandLeft", fontName="GigTaxSans-Bold", fontSize=16, textColor=colors.white, leading=19))
    ss.add(ParagraphStyle(name="GTBrandRight", fontName="GigTaxSans", fontSize=10, textColor=colors.white, alignment=TA_RIGHT, leading=13))
    ss.add(ParagraphStyle(name="GTBody", fontName="GigTaxSans", fontSize=9.5, textColor=NAVY, leading=13))
    ss.add(ParagraphStyle(name="GTInfoBody", fontName="GigTaxSans", fontSize=9, textColor=NAVY, leading=12))
    ss.add(ParagraphStyle(name="GTMuted", parent=ss["GTBody"], textColor=MUTED, fontSize=8.5))
    ss.add(ParagraphStyle(name="GTHeading2", parent=ss["GTBody"], fontName="GigTaxSans-Bold", fontSize=13, textColor=ACCENT_DARK, spaceBefore=16, spaceAfter=6))
    ss.add(ParagraphStyle(name="GTHeading3", parent=ss["GTBody"], fontName="GigTaxSans-Bold", fontSize=10, textColor=NAVY, spaceBefore=10, spaceAfter=3))
    ss.add(ParagraphStyle(name="GTTableHeader", parent=ss["GTBody"], fontName="GigTaxSans-Bold", fontSize=8.5, textColor=ACCENT_DARK))
    ss.add(ParagraphStyle(name="GTTableHeaderRight", parent=ss["GTTableHeader"], alignment=TA_RIGHT))
    ss.add(ParagraphStyle(name="GTTableCell", parent=ss["GTBody"], fontSize=9))
    ss.add(ParagraphStyle(name="GTTableCellRight", parent=ss["GTTableCell"], alignment=TA_RIGHT))
    ss.add(ParagraphStyle(name="GTTableCellBoldRight", parent=ss["GTTableCellRight"], fontName="GigTaxSans-Bold"))
    return ss


class _FooterCanvas(Canvas):
    """Draws the disclaimer + 'Page X of Y' as a running footer on every page instead
    of flowing them as normal story content. The disclaimer used to be the last
    Paragraph in the story, which meant it could get pushed onto its own near-empty
    page whenever the preceding tables didn't leave quite enough room on the page
    before — a footer is the correct place for it precisely because it can't strand.
    'of Y' requires knowing the total page count, which reportlab can only tell you
    after the whole document has been laid out, hence the two-pass buffer-then-draw
    approach below (the standard reportlab recipe for numbered pages).
    """

    def __init__(self, *args, **kwargs):
        Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_footer(page_count)
            Canvas.showPage(self)
        Canvas.save(self)

    def _draw_footer(self, page_count: int) -> None:
        self.saveState()
        line_y = 1.7 * cm
        self.setStrokeColor(DIVIDER)
        self.setLineWidth(0.5)
        self.line(2 * cm, line_y, PAGE_WIDTH - 2 * cm, line_y)

        # A Paragraph (not drawString) so this wraps onto a second line rather than
        # running into the page-number text on a narrow page — drawString has no
        # wrapping of its own and the two silently overlapped before this fix.
        disclaimer = Paragraph(
            "This is a self-assessment estimate generated by GigTax based on the transactions you "
            "reviewed and approved. It is not a substitute for professional tax advice.",
            ParagraphStyle(name="_FooterDisclaimer", fontName="GigTaxSans-Oblique", fontSize=7.5, textColor=MUTED, leading=9.5),
        )
        _, disclaimer_height = disclaimer.wrap(PAGE_WIDTH - 4 * cm, 2 * cm)
        disclaimer_top = line_y - 0.2 * cm
        disclaimer.drawOn(self, 2 * cm, disclaimer_top - disclaimer_height)

        self.setFont("GigTaxSans", 8)
        self.setFillColor(MUTED)
        self.drawRightString(PAGE_WIDTH - 2 * cm, disclaimer_top - disclaimer_height - 0.4 * cm, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def _format_period(period_start: datetime | None, period_end: datetime | None) -> str:
    if period_start is None or period_end is None:
        return "No approved records for this tax year yet"
    if period_start.date() == period_end.date():
        return period_start.strftime("%d %b %Y")
    return f"{period_start.strftime('%d %b %Y')} – {period_end.strftime('%d %b %Y')}"


def _money(amount: float, *, negative: bool = False) -> str:
    """`negative` prepends the minus sign the web page shows for deductions/capital
    allowances/reliefs (see ReportsPage.tsx's `-computationQuery.data.total_deductions`
    etc.) — this function is only ever handed a magnitude. Matches the app's own
    `formatNaira` (Intl.NumberFormat('en-NG', {style:'currency', currency:'NGN'})),
    which renders as e.g. '₦150,000.00' with no space after the symbol.
    """
    sign = "-" if negative and amount > 0 else ""
    return f"{sign}₦{amount:,.2f}"


def _header_bar(tax_year: str, styles: dict) -> Table:
    bar = Table(
        [[Paragraph("GigTax", styles["GTBrandLeft"]), Paragraph(f"Self-Assessment Report &mdash; {tax_year}", styles["GTBrandRight"])]],
        colWidths=[CONTENT_WIDTH * 0.4, CONTENT_WIDTH * 0.6],
    )
    bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT_DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 14),
        ("RIGHTPADDING", (-1, 0), (-1, 0), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    return bar


def _info_box(info_pairs: list[tuple[str, str]], styles: dict) -> Table:
    # Two-up so related facts sit on the same line instead of one long single-column
    # list — (label, value) pairs, two per row.
    rows = []
    for i in range(0, len(info_pairs), 2):
        pair = info_pairs[i : i + 2]
        row = [Paragraph(f"<font color='#4a4d50'>{label}</font> <b>{value}</b>", styles["GTInfoBody"]) for label, value in pair]
        if len(row) == 1:
            row.append("")
        rows.append(row)
    table = Table(rows, colWidths=[CONTENT_WIDTH / 2, CONTENT_WIDTH / 2])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.75, DIVIDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


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
    styles = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2.2 * cm, leftMargin=2 * cm, rightMargin=2 * cm,
    )

    info_pairs = [
        ("Prepared for", user_name),
        ("TIN", tin or "Not provided"),
        ("State of Residence", state_residence or "Not provided"),
        ("Occupation", occupation_type or "Not provided"),
        ("Records Covered", _format_period(period_start, period_end)),
        ("Generated", datetime.now().strftime("%Y-%m-%d %H:%M")),
    ]

    story = [
        _header_bar(tax_year, styles),
        Spacer(1, 0.4 * cm),
        _info_box(info_pairs, styles),
        Spacer(1, 0.5 * cm),
    ]

    if result.minimum_wage_exempt:
        # An additional notice, not a replacement for the summary below — the web
        # Reports page shows this same banner above its Tax Summary table, never
        # instead of it, so the PDF matches rather than stopping short.
        exempt_box = Table(
            [[Paragraph(
                "Total income is at or below the National Minimum Wage &mdash; fully exempt under "
                "NTA 2025 s.58 / s.162(1)(t).",
                ParagraphStyle(name="GTExempt", parent=styles["GTBody"], textColor=EXEMPT_GREEN, fontName="GigTaxSans-Bold"),
            )]],
            colWidths=[CONTENT_WIDTH],
        )
        exempt_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), EXEMPT_TINT),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(exempt_box)
        story.append(Spacer(1, 0.4 * cm))

    def _table_header_style(col_count: int) -> TableStyle:
        return TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT_TINT),
            ("LINEBELOW", (0, 0), (-1, 0), 0.75, ACCENT),
            ("LINEBELOW", (0, 1), (-1, -2), 0.4, DIVIDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])

    story.append(Paragraph("Summary", styles["GTHeading2"]))
    summary_rows = [
        [Paragraph("Category", styles["GTTableHeader"]), Paragraph("Amount", styles["GTTableHeaderRight"])],
        [Paragraph("Total Income (NTA 2025 s.28)", styles["GTTableCell"]), Paragraph(_money(result.total_income), styles["GTTableCellRight"])],
        [Paragraph("Allowable Deductions (ss.20-21)", styles["GTTableCell"]), Paragraph(_money(result.total_deductions, negative=True), styles["GTTableCellRight"])],
        [Paragraph("Capital Allowances (First Schedule)", styles["GTTableCell"]), Paragraph(_money(result.total_capital_allowances, negative=True), styles["GTTableCellRight"])],
        [Paragraph("Statutory Reliefs (s.30)", styles["GTTableCell"]), Paragraph(_money(result.total_reliefs, negative=True), styles["GTTableCellRight"])],
        [Paragraph("Chargeable Income", styles["GTTableCell"]), Paragraph(_money(result.chargeable_income), styles["GTTableCellRight"])],
        [
            Paragraph("Net Tax Payable (Fourth Schedule, s.58)", ParagraphStyle(name="GTNetLabel", parent=styles["GTTableCell"], fontName="GigTaxSans-Bold", textColor=ACCENT_DARK)),
            Paragraph(_money(result.net_tax), styles["GTTableCellBoldRight"]),
        ],
    ]
    summary_table = Table(summary_rows, colWidths=[CONTENT_WIDTH * 0.65, CONTENT_WIDTH * 0.35])
    summary_style = _table_header_style(2)
    summary_style.add("BACKGROUND", (0, -1), (-1, -1), ACCENT_TINT)
    summary_style.add("LINEABOVE", (0, -1), (-1, -1), 0.75, ACCENT)
    summary_table.setStyle(summary_style)
    story.append(summary_table)
    story.append(Spacer(1, 0.5 * cm))

    item_sections = [
        ("Income", items.get("income_items", [])),
        ("Allowable Deductions", items.get("deduction_items", [])),
        ("Capital Allowances", items.get("capital_allowance_items", [])),
        ("Statutory Reliefs", items.get("relief_items", [])),
    ]
    if any(entries for _, entries in item_sections):
        story.append(Paragraph("Itemized Breakdown", styles["GTHeading2"]))
        for section_label, entries in item_sections:
            if not entries:
                continue
            story.append(Paragraph(section_label, styles["GTHeading3"]))
            # Deduction and capital allowance items carry `rate`/`gross_amount`
            # (see reporting_helpers.build_itemized_breakdown and
            # loader.load_capital_allowance_items) — shown as their own columns
            # so a reader can see, e.g., "100%" for a normal expense versus a
            # home-office category's user-set percentage, and the original
            # amount that rate was applied to.
            has_rate = any(entry.get("rate") is not None for entry in entries)
            if has_rate:
                item_rows = [[
                    Paragraph("Category", styles["GTTableHeader"]),
                    Paragraph("Gross Amount", styles["GTTableHeaderRight"]),
                    Paragraph("Rate", styles["GTTableHeaderRight"]),
                    Paragraph("Amount Deducted", styles["GTTableHeaderRight"]),
                ]]
                for entry in entries:
                    item_rows.append([
                        Paragraph(entry["category_name"], styles["GTTableCell"]),
                        Paragraph(_money(entry.get("gross_amount", entry["amount"])), styles["GTTableCellRight"]),
                        Paragraph(f"{entry['rate']:.0f}%", styles["GTTableCellRight"]),
                        Paragraph(_money(entry["amount"]), styles["GTTableCellRight"]),
                    ])
                col_widths = [CONTENT_WIDTH * 0.4, CONTENT_WIDTH * 0.22, CONTENT_WIDTH * 0.13, CONTENT_WIDTH * 0.25]
            else:
                item_rows = [[Paragraph("Category", styles["GTTableHeader"]), Paragraph("Amount", styles["GTTableHeaderRight"])]]
                for entry in entries:
                    item_rows.append([
                        Paragraph(entry["category_name"], styles["GTTableCell"]),
                        Paragraph(_money(entry["amount"]), styles["GTTableCellRight"]),
                    ])
                col_widths = [CONTENT_WIDTH * 0.65, CONTENT_WIDTH * 0.35]
            item_table = Table(item_rows, colWidths=col_widths)
            item_table.setStyle(_table_header_style(len(col_widths)))
            story.append(item_table)
            story.append(Spacer(1, 0.3 * cm))

    # Skipped when there's nothing to show — minimum-wage exemption means no band
    # actually applied, so band_breakdown comes back empty from the engine (matching
    # the web Reports page, which gates this same section on the same condition).
    if result.band_breakdown:
        story.append(Paragraph("Band-by-band Computation (Fourth Schedule)", styles["GTHeading2"]))
        band_rows = [[
            Paragraph("Rate", styles["GTTableHeader"]),
            Paragraph("Amount in Band", styles["GTTableHeaderRight"]),
            Paragraph("Tax", styles["GTTableHeaderRight"]),
        ]]
        for band in result.band_breakdown:
            band_rows.append([
                Paragraph(f"{band.rate * 100:.0f}%", styles["GTTableCell"]),
                Paragraph(_money(band.amount_in_band), styles["GTTableCellRight"]),
                Paragraph(_money(band.tax), styles["GTTableCellRight"]),
            ])
        band_table = Table(band_rows, colWidths=[CONTENT_WIDTH * 0.2, CONTENT_WIDTH * 0.4, CONTENT_WIDTH * 0.4])
        band_table.setStyle(_table_header_style(3))
        story.append(band_table)

    doc.build(story, canvasmaker=_FooterCanvas)
    return buffer.getvalue()
