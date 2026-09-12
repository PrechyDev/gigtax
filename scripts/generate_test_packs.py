"""Generates the synthetic bank-statement test pack under scripts/fixtures/test_packs/.

Purpose: give the ingestion pipeline (parsing -> sanitization -> AI categorization ->
review -> tax computation) realistic, varied inputs to exercise locally, without ever
touching a real user's real bank statement. Every name, account number, and TIN below
is fabricated for this purpose.

Four fictional user profiles, chosen to exercise different corners of the tax engine
and the ingestion pipeline:

  1. Adaeze Chukwu   (Lagos,  CSV)  - freelance developer, home-office claim, one
                                      capital asset (laptop), tests the mid-band rates
                                      and the home-office deduction-rate split.
  2. Tunde Bakare     (Oyo,    XLSX) - content creator, deliberately exported with a
                                      messy multi-row header block above the real
                                      table (as many real bank Excel exports have),
                                      to stress-test the parser beyond a clean sheet.
  3. Chiamaka Okoro   (Osun,   PDF)  - digital vendor, vehicle capital asset (Class 3),
                                      life assurance relief.
  4. Ibrahim Suleiman (FCT,    CSV + PDF, two files) - low/borderline income to test
                                      the National Minimum Wage exemption boundary,
                                      AND split across two files in two different
                                      formats (switched banks mid-year) to exercise
                                      the "multiple files at once, independently
                                      processed" ingestion requirement (see
                                      docs/SYSTEM_SPECIFICATION.md 3.2) and
                                      loader.get_records_period spanning both.

Run with: poetry run python ../scripts/generate_test_packs.py   (from backend/), or
          poetry run python scripts/generate_test_packs.py      (from Implementation/,
          using the backend poetry env: cd backend && poetry run python ../scripts/generate_test_packs.py)
"""
import os

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "test_packs")


def _with_balance(rows: list[dict], opening_balance: float) -> list[dict]:
    balance = opening_balance
    out = []
    for row in rows:
        balance += (row.get("credit") or 0) - (row.get("debit") or 0)
        out.append({**row, "balance": round(balance, 2)})
    return out


def _fmt(amount):
    return f"{amount:,.2f}" if amount else ""


def render_csv(rows: list[dict], path: str) -> None:
    df = pd.DataFrame([
        {
            "Date": r["date"],
            "Narration": r["narration"],
            "Debit": r.get("debit") or "",
            "Credit": r.get("credit") or "",
            "Balance": r["balance"],
        }
        for r in rows
    ])
    df.to_csv(path, index=False)


def render_xlsx(rows: list[dict], path: str, preamble: list[str] | None = None) -> None:
    df = pd.DataFrame([
        {
            "Date": r["date"],
            "Narration": r["narration"],
            "Debit": r.get("debit") or "",
            "Credit": r.get("credit") or "",
            "Balance": r["balance"],
        }
        for r in rows
    ])
    if not preamble:
        df.to_excel(path, index=False)
        return

    # Deliberately messy: a metadata block (account name/number/period, as many real
    # bank Excel exports include) sits above the real header row, so this file is
    # NOT a clean startrow=0 table — good for stress-testing the parser rather than
    # only ever feeding it the ideal case.
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame({0: preamble}).to_excel(
            writer, index=False, header=False, startrow=0, sheet_name="Statement"
        )
        df.to_excel(writer, index=False, startrow=len(preamble) + 1, sheet_name="Statement")


def render_pdf(
    rows: list[dict],
    path: str,
    *,
    bank_name: str,
    account_name: str,
    account_number: str,
    statement_period: str,
) -> None:
    buffer_doc = SimpleDocTemplate(path, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(bank_name, styles["Title"]),
        Paragraph("Account Statement", styles["Heading2"]),
        Paragraph(f"Account Name: {account_name}", styles["Normal"]),
        Paragraph(f"Account Number: {account_number}", styles["Normal"]),
        Paragraph(f"Statement Period: {statement_period}", styles["Normal"]),
        Paragraph("Currency: NGN", styles["Normal"]),
        Spacer(1, 0.5 * cm),
    ]

    table_data = [["Date", "Narration", "Debit", "Credit", "Balance"]] + [
        [r["date"], r["narration"], _fmt(r.get("debit")), _fmt(r.get("credit")), _fmt(r["balance"])]
        for r in rows
    ]
    table = Table(table_data, colWidths=[2.2 * cm, 7.3 * cm, 2.7 * cm, 2.7 * cm, 3 * cm], repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "This is a synthetic statement generated for GigTax software testing. It does not "
        "represent a real account or a real person.",
        styles["Italic"],
    ))
    buffer_doc.build(story)


# ---------------------------------------------------------------------------
# Profile 1 — Adaeze Chukwu, Lagos, freelance developer, CSV, full year 2026
# ---------------------------------------------------------------------------

def profile_1_rows() -> list[dict]:
    rows = [
        {"date": "2026-01-05", "narration": "RENT PAYMENT - LANDLORD MR BALOGUN (12 MONTHS)", "debit": 1_800_000},
        {"date": "2026-01-10", "narration": "PAYONEER TRANSFER - UPWORK INC WITHDRAWAL", "credit": 480_000},
        {"date": "2026-01-14", "narration": "GITHUB INC - COPILOT + ACTIONS SUBSCRIPTION", "debit": 18_500},
        {"date": "2026-01-18", "narration": "SPECTRANET LTD - MONTHLY DATA PLAN", "debit": 26_000},
        {"date": "2026-01-22", "narration": "IKEDC - ELECTRICITY BILL (WORKSPACE)", "debit": 38_000},
        {"date": "2026-02-08", "narration": "PAYONEER TRANSFER - UPWORK INC WITHDRAWAL", "credit": 512_000},
        {"date": "2026-02-11", "narration": "SLOT SYSTEMS LIMITED - MACBOOK PRO 14 PURCHASE", "debit": 1_450_000},
        {"date": "2026-02-19", "narration": "AWS - CLOUD HOSTING CHARGE", "debit": 21_400},
        {"date": "2026-02-24", "narration": "TRANSFER FROM MOTHER - MRS N CHUKWU", "credit": 100_000},
        {"date": "2026-03-06", "narration": "DEEL INC - CONTRACT PAYOUT (US CLIENT)", "credit": 610_000},
        {"date": "2026-03-12", "narration": "GITHUB INC - COPILOT + ACTIONS SUBSCRIPTION", "debit": 18_500},
        {"date": "2026-03-18", "narration": "SPECTRANET LTD - MONTHLY DATA PLAN", "debit": 26_000},
        {"date": "2026-03-23", "narration": "IKEDC - ELECTRICITY BILL (WORKSPACE)", "debit": 41_500},
        {"date": "2026-03-29", "narration": "STANBIC IBTC PENSION - VOLUNTARY CONTRIBUTION", "debit": 60_000},
        {"date": "2026-04-09", "narration": "PAYONEER TRANSFER - UPWORK INC WITHDRAWAL", "credit": 455_000},
        {"date": "2026-04-15", "narration": "TRANSFER TO OWN SAVINGS ACCOUNT - GTBANK", "debit": 200_000},
        {"date": "2026-04-20", "narration": "AWS - CLOUD HOSTING CHARGE", "debit": 19_800},
        {"date": "2026-05-07", "narration": "PAYONEER TRANSFER - UPWORK INC WITHDRAWAL", "credit": 498_000},
        {"date": "2026-05-14", "narration": "GITHUB INC - COPILOT + ACTIONS SUBSCRIPTION", "debit": 18_500},
        {"date": "2026-05-18", "narration": "SPECTRANET LTD - MONTHLY DATA PLAN", "debit": 26_000},
        {"date": "2026-05-25", "narration": "IKEDC - ELECTRICITY BILL (WORKSPACE)", "debit": 39_200},
        {"date": "2026-06-10", "narration": "DEEL INC - CONTRACT PAYOUT (US CLIENT)", "credit": 590_000},
        {"date": "2026-06-16", "narration": "AWS - CLOUD HOSTING CHARGE", "debit": 22_100},
        {"date": "2026-06-29", "narration": "STANBIC IBTC PENSION - VOLUNTARY CONTRIBUTION", "debit": 60_000},
        {"date": "2026-07-08", "narration": "PAYONEER TRANSFER - UPWORK INC WITHDRAWAL", "credit": 470_000},
        {"date": "2026-07-14", "narration": "GITHUB INC - COPILOT + ACTIONS SUBSCRIPTION", "debit": 18_500},
        {"date": "2026-07-18", "narration": "SPECTRANET LTD - MONTHLY DATA PLAN", "debit": 26_000},
        {"date": "2026-07-24", "narration": "IKEDC - ELECTRICITY BILL (WORKSPACE)", "debit": 43_000},
        {"date": "2026-08-11", "narration": "PAYONEER TRANSFER - UPWORK INC WITHDRAWAL", "credit": 505_000},
        {"date": "2026-08-19", "narration": "AWS - CLOUD HOSTING CHARGE", "debit": 20_600},
        {"date": "2026-09-09", "narration": "DEEL INC - CONTRACT PAYOUT (US CLIENT)", "credit": 615_000},
        {"date": "2026-09-15", "narration": "GITHUB INC - COPILOT + ACTIONS SUBSCRIPTION", "debit": 18_500},
        {"date": "2026-09-21", "narration": "SPECTRANET LTD - MONTHLY DATA PLAN", "debit": 26_000},
        {"date": "2026-09-29", "narration": "STANBIC IBTC PENSION - VOLUNTARY CONTRIBUTION", "debit": 60_000},
        {"date": "2026-10-07", "narration": "PAYONEER TRANSFER - UPWORK INC WITHDRAWAL", "credit": 488_000},
        {"date": "2026-10-20", "narration": "IKEDC - ELECTRICITY BILL (WORKSPACE)", "debit": 40_500},
        {"date": "2026-10-26", "narration": "AWS - CLOUD HOSTING CHARGE", "debit": 23_000},
        {"date": "2026-11-10", "narration": "PAYONEER TRANSFER - UPWORK INC WITHDRAWAL", "credit": 522_000},
        {"date": "2026-11-16", "narration": "GITHUB INC - COPILOT + ACTIONS SUBSCRIPTION", "debit": 18_500},
        {"date": "2026-11-22", "narration": "SPECTRANET LTD - MONTHLY DATA PLAN", "debit": 26_000},
        {"date": "2026-12-08", "narration": "DEEL INC - CONTRACT PAYOUT (US CLIENT)", "credit": 640_000},
        {"date": "2026-12-15", "narration": "IKEDC - ELECTRICITY BILL (WORKSPACE)", "debit": 45_000},
        {"date": "2026-12-29", "narration": "STANBIC IBTC PENSION - VOLUNTARY CONTRIBUTION", "debit": 60_000},
    ]
    return _with_balance(rows, opening_balance=2_450_000)


# ---------------------------------------------------------------------------
# Profile 2 — Tunde Bakare, Oyo, content creator, XLSX (messy header), 2026
# ---------------------------------------------------------------------------

def profile_2_rows() -> list[dict]:
    rows = [
        {"date": "2026-01-06", "narration": "GOOGLE ADSENSE PAYMENT - YOUTUBE PARTNER", "credit": 320_000},
        {"date": "2026-01-13", "narration": "META PLATFORMS - ADS MANAGER CAMPAIGN CHARGE", "debit": 58_000},
        {"date": "2026-01-20", "narration": "PAYMENT TO FEMI EDITS - VIDEO EDITING SERVICES", "debit": 80_000},
        {"date": "2026-01-27", "narration": "MTN NIGERIA - DATA BUNDLE SUBSCRIPTION", "debit": 21_000},
        {"date": "2026-02-05", "narration": "GOOGLE ADSENSE PAYMENT - YOUTUBE PARTNER", "credit": 355_000},
        {"date": "2026-02-12", "narration": "GLOBACOM NG - SPONSORED CONTENT PAYMENT", "credit": 500_000},
        {"date": "2026-02-18", "narration": "PAYMENT TO FEMI EDITS - VIDEO EDITING SERVICES", "debit": 80_000},
        {"date": "2026-02-26", "narration": "CANON NIGERIA LTD - EOS R6 CAMERA PURCHASE", "debit": 2_100_000},
        {"date": "2026-03-06", "narration": "GOOGLE ADSENSE PAYMENT - YOUTUBE PARTNER", "credit": 298_000},
        {"date": "2026-03-14", "narration": "META PLATFORMS - ADS MANAGER CAMPAIGN CHARGE", "debit": 62_000},
        {"date": "2026-03-21", "narration": "HYGEIA HMO - ANNUAL PREMIUM", "debit": 180_000},
        {"date": "2026-04-06", "narration": "GOOGLE ADSENSE PAYMENT - YOUTUBE PARTNER", "credit": 410_000},
        {"date": "2026-04-15", "narration": "PAYMENT TO FEMI EDITS - VIDEO EDITING SERVICES", "debit": 85_000},
        {"date": "2026-04-22", "narration": "JUMIA NG - SALE OF OLD PHONE", "credit": 85_000},
        {"date": "2026-05-06", "narration": "GOOGLE ADSENSE PAYMENT - YOUTUBE PARTNER", "credit": 375_000},
        {"date": "2026-05-13", "narration": "META PLATFORMS - ADS MANAGER CAMPAIGN CHARGE", "debit": 59_000},
        {"date": "2026-05-27", "narration": "MTN NIGERIA - DATA BUNDLE SUBSCRIPTION", "debit": 21_000},
        {"date": "2026-06-05", "narration": "GOOGLE ADSENSE PAYMENT - YOUTUBE PARTNER", "credit": 430_000},
        {"date": "2026-06-12", "narration": "GLOBACOM NG - SPONSORED CONTENT PAYMENT", "credit": 500_000},
        {"date": "2026-06-19", "narration": "PAYMENT TO FEMI EDITS - VIDEO EDITING SERVICES", "debit": 85_000},
        {"date": "2026-07-06", "narration": "GOOGLE ADSENSE PAYMENT - YOUTUBE PARTNER", "credit": 460_000},
        {"date": "2026-07-14", "narration": "META PLATFORMS - ADS MANAGER CAMPAIGN CHARGE", "debit": 65_000},
        {"date": "2026-08-06", "narration": "GOOGLE ADSENSE PAYMENT - YOUTUBE PARTNER", "credit": 505_000},
        {"date": "2026-08-15", "narration": "PAYMENT TO FEMI EDITS - VIDEO EDITING SERVICES", "debit": 90_000},
        {"date": "2026-08-22", "narration": "MTN NIGERIA - DATA BUNDLE SUBSCRIPTION", "debit": 22_000},
        {"date": "2026-09-06", "narration": "GOOGLE ADSENSE PAYMENT - YOUTUBE PARTNER", "credit": 540_000},
        {"date": "2026-09-14", "narration": "META PLATFORMS - ADS MANAGER CAMPAIGN CHARGE", "debit": 67_000},
        {"date": "2026-10-06", "narration": "GOOGLE ADSENSE PAYMENT - YOUTUBE PARTNER", "credit": 610_000},
        {"date": "2026-10-13", "narration": "GLOBACOM NG - SPONSORED CONTENT PAYMENT", "credit": 500_000},
        {"date": "2026-10-20", "narration": "PAYMENT TO FEMI EDITS - VIDEO EDITING SERVICES", "debit": 92_000},
        {"date": "2026-11-06", "narration": "GOOGLE ADSENSE PAYMENT - YOUTUBE PARTNER", "credit": 650_000},
        {"date": "2026-11-14", "narration": "META PLATFORMS - ADS MANAGER CAMPAIGN CHARGE", "debit": 70_000},
        {"date": "2026-12-06", "narration": "GOOGLE ADSENSE PAYMENT - YOUTUBE PARTNER", "credit": 700_000},
        {"date": "2026-12-15", "narration": "PAYMENT TO FEMI EDITS - VIDEO EDITING SERVICES", "debit": 95_000},
        {"date": "2026-12-20", "narration": "MTN NIGERIA - DATA BUNDLE SUBSCRIPTION", "debit": 22_000},
    ]
    return _with_balance(rows, opening_balance=1_200_000)


# ---------------------------------------------------------------------------
# Profile 3 — Chiamaka Okoro, Osun, digital vendor, PDF, 2026
# ---------------------------------------------------------------------------

def profile_3_rows() -> list[dict]:
    rows = [
        {"date": "2026-01-08", "narration": "INSTAGRAM SHOP SALES - VARIOUS CUSTOMERS", "credit": 620_000},
        {"date": "2026-01-16", "narration": "PAYMENT TO DELIVERY RIDER - IBRAHIM MUSA", "debit": 42_000},
        {"date": "2026-01-24", "narration": "META PLATFORMS - INSTAGRAM ADS", "debit": 30_000},
        {"date": "2026-02-09", "narration": "INSTAGRAM SHOP SALES - VARIOUS CUSTOMERS", "credit": 710_000},
        {"date": "2026-02-18", "narration": "AUTOCHEK NIGERIA - TRICYCLE PURCHASE (DELIVERY)", "debit": 1_200_000},
        {"date": "2026-02-26", "narration": "PAYMENT TO DELIVERY RIDER - IBRAHIM MUSA", "debit": 42_000},
        {"date": "2026-03-10", "narration": "INSTAGRAM SHOP SALES - VARIOUS CUSTOMERS", "credit": 585_000},
        {"date": "2026-03-19", "narration": "AIICO INSURANCE - LIFE POLICY PREMIUM", "debit": 60_000},
        {"date": "2026-03-27", "narration": "META PLATFORMS - INSTAGRAM ADS", "debit": 32_000},
        {"date": "2026-04-11", "narration": "INSTAGRAM SHOP SALES - VARIOUS CUSTOMERS", "credit": 640_000},
        {"date": "2026-04-20", "narration": "PAYMENT TO DELIVERY RIDER - IBRAHIM MUSA", "debit": 45_000},
        {"date": "2026-05-09", "narration": "INSTAGRAM SHOP SALES - VARIOUS CUSTOMERS", "credit": 705_000},
        {"date": "2026-05-18", "narration": "META PLATFORMS - INSTAGRAM ADS", "debit": 35_000},
        {"date": "2026-06-08", "narration": "INSTAGRAM SHOP SALES - VARIOUS CUSTOMERS", "credit": 590_000},
        {"date": "2026-06-19", "narration": "AIICO INSURANCE - LIFE POLICY PREMIUM", "debit": 60_000},
        {"date": "2026-06-27", "narration": "PAYMENT TO DELIVERY RIDER - IBRAHIM MUSA", "debit": 45_000},
        {"date": "2026-07-10", "narration": "INSTAGRAM SHOP SALES - VARIOUS CUSTOMERS", "credit": 665_000},
        {"date": "2026-07-21", "narration": "META PLATFORMS - INSTAGRAM ADS", "debit": 34_000},
        {"date": "2026-08-09", "narration": "INSTAGRAM SHOP SALES - VARIOUS CUSTOMERS", "credit": 720_000},
        {"date": "2026-08-20", "narration": "PAYMENT TO DELIVERY RIDER - IBRAHIM MUSA", "debit": 48_000},
        {"date": "2026-09-08", "narration": "INSTAGRAM SHOP SALES - VARIOUS CUSTOMERS", "credit": 610_000},
        {"date": "2026-09-19", "narration": "AIICO INSURANCE - LIFE POLICY PREMIUM", "debit": 60_000},
        {"date": "2026-09-27", "narration": "META PLATFORMS - INSTAGRAM ADS", "debit": 36_000},
        {"date": "2026-10-10", "narration": "INSTAGRAM SHOP SALES - VARIOUS CUSTOMERS", "credit": 745_000},
        {"date": "2026-10-21", "narration": "PAYMENT TO DELIVERY RIDER - IBRAHIM MUSA", "debit": 48_000},
        {"date": "2026-11-09", "narration": "INSTAGRAM SHOP SALES - VARIOUS CUSTOMERS", "credit": 810_000},
        {"date": "2026-11-20", "narration": "META PLATFORMS - INSTAGRAM ADS", "debit": 40_000},
        {"date": "2026-12-08", "narration": "INSTAGRAM SHOP SALES - VARIOUS CUSTOMERS", "credit": 890_000},
        {"date": "2026-12-19", "narration": "AIICO INSURANCE - LIFE POLICY PREMIUM", "debit": 60_000},
        {"date": "2026-12-27", "narration": "PAYMENT TO DELIVERY RIDER - IBRAHIM MUSA", "debit": 50_000},
    ]
    return _with_balance(rows, opening_balance=180_000)


# ---------------------------------------------------------------------------
# Profile 4 — Ibrahim Suleiman, FCT, low-income remote consultant, split
# across two files/formats (bank switch mid-year): CSV Jan-Jun, PDF Jul-Dec.
# Retainer kept low enough that annual total sits under the National Minimum
# Wage threshold (NGN 840,000/yr) to exercise the minimum_wage_exempt path.
# ---------------------------------------------------------------------------

def profile_4_rows_h1() -> list[dict]:
    rows = [
        {"date": "2026-01-15", "narration": "TECHCORP CONSULTING LTD - MONTHLY RETAINER", "credit": 58_000},
        {"date": "2026-01-29", "narration": "MTN NIGERIA - DATA BUNDLE SUBSCRIPTION", "debit": 8_000},
        {"date": "2026-02-15", "narration": "TECHCORP CONSULTING LTD - MONTHLY RETAINER", "credit": 58_000},
        {"date": "2026-03-15", "narration": "TECHCORP CONSULTING LTD - MONTHLY RETAINER", "credit": 60_000},
        {"date": "2026-03-29", "narration": "MTN NIGERIA - DATA BUNDLE SUBSCRIPTION", "debit": 8_000},
        {"date": "2026-04-15", "narration": "TECHCORP CONSULTING LTD - MONTHLY RETAINER", "credit": 60_000},
        {"date": "2026-05-15", "narration": "TECHCORP CONSULTING LTD - MONTHLY RETAINER", "credit": 60_000},
        {"date": "2026-05-29", "narration": "MTN NIGERIA - DATA BUNDLE SUBSCRIPTION", "debit": 8_000},
        {"date": "2026-06-15", "narration": "TECHCORP CONSULTING LTD - MONTHLY RETAINER", "credit": 60_000},
    ]
    return _with_balance(rows, opening_balance=45_000)


def profile_4_rows_h2(opening_balance: float) -> list[dict]:
    rows = [
        {"date": "2026-07-16", "narration": "TECHCORP CONSULTING LTD - MONTHLY RETAINER", "credit": 60_000},
        {"date": "2026-07-30", "narration": "9MOBILE - DATA BUNDLE SUBSCRIPTION", "debit": 7_500},
        {"date": "2026-08-16", "narration": "TECHCORP CONSULTING LTD - MONTHLY RETAINER", "credit": 62_000},
        {"date": "2026-09-16", "narration": "TECHCORP CONSULTING LTD - MONTHLY RETAINER", "credit": 62_000},
        {"date": "2026-09-30", "narration": "9MOBILE - DATA BUNDLE SUBSCRIPTION", "debit": 7_500},
        {"date": "2026-10-16", "narration": "TECHCORP CONSULTING LTD - MONTHLY RETAINER", "credit": 62_000},
        {"date": "2026-11-16", "narration": "TECHCORP CONSULTING LTD - MONTHLY RETAINER", "credit": 62_000},
        {"date": "2026-11-30", "narration": "9MOBILE - DATA BUNDLE SUBSCRIPTION", "debit": 7_500},
        {"date": "2026-12-16", "narration": "TECHCORP CONSULTING LTD - MONTHLY RETAINER", "credit": 64_000},
    ]
    return _with_balance(rows, opening_balance=opening_balance)


def main() -> None:
    p1_dir = os.path.join(OUT_DIR, "profile_1_adaeze_chukwu_lagos_freelance_dev")
    p2_dir = os.path.join(OUT_DIR, "profile_2_tunde_bakare_oyo_content_creator")
    p3_dir = os.path.join(OUT_DIR, "profile_3_chiamaka_okoro_osun_digital_vendor")
    p4_dir = os.path.join(OUT_DIR, "profile_4_ibrahim_suleiman_fct_low_income")
    for d in (p1_dir, p2_dir, p3_dir, p4_dir):
        os.makedirs(d, exist_ok=True)

    render_csv(profile_1_rows(), os.path.join(p1_dir, "moniepoint_statement_2026.csv"))

    render_xlsx(
        profile_2_rows(),
        os.path.join(p2_dir, "gtbank_statement_2026.xlsx"),
        preamble=[
            "GUARANTY TRUST BANK PLC",
            "Account Name: Tunde Bakare",
            "Account Number: 0123456789",
            "Statement Period: 01-Jan-2026 to 31-Dec-2026",
            "Currency: NGN",
        ],
    )

    render_pdf(
        profile_3_rows(),
        os.path.join(p3_dir, "kuda_statement_2026.pdf"),
        bank_name="Kuda Microfinance Bank",
        account_name="Chiamaka Okoro",
        account_number="2076543210",
        statement_period="01 Jan 2026 - 31 Dec 2026",
    )

    h1 = profile_4_rows_h1()
    render_csv(h1, os.path.join(p4_dir, "access_bank_statement_jan_to_jun_2026.csv"))
    h2 = profile_4_rows_h2(opening_balance=h1[-1]["balance"])
    render_pdf(
        h2,
        os.path.join(p4_dir, "opay_statement_jul_to_dec_2026.pdf"),
        bank_name="OPay Digital Services Limited",
        account_name="Ibrahim Suleiman",
        account_number="8098765432",
        statement_period="01 Jul 2026 - 31 Dec 2026",
    )

    print(f"Test pack written under {OUT_DIR}")


if __name__ == "__main__":
    main()
