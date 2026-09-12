# Standard Self-Assessment Report — Template Specification

This documents the shape of the PDF GigTax generates at `GET /tax-computations/{tax_year}/report`, built by `modules/reporting/generator.py:build_report_pdf`. It exists as a spec, in one place, of what "the report" is supposed to contain — the actual layout logic lives in the generator module; this file explains *why* each section is there and where its numbers come from.

## 1. Header

| Field | Source |
|---|---|
| Tax Year | route path param |
| Prepared for | `user.name` |
| TIN | `user.tin` (shows "Not provided" if unset — a self-reporter can still generate and use the report before they've registered for a TIN) |
| State of Residence | `user.state_residence` |
| Occupation | `user.occupation_type` |
| Records Covered | earliest–latest date among this year's **APPROVED** transactions (`loader.get_records_period`) — deliberately *not* a fixed "Jan 1 – Dec 31" label. A user with records only from March onward sees that honestly rather than a header implying full-year coverage they don't have. |
| Generated | server timestamp at download time |

## 2. Summary table

Total Income → Allowable Deductions → Capital Allowances → Statutory Reliefs → Chargeable Income → Net Tax Payable, each tagged with the NTA 2025 section it maps to (s.28 income, ss.20–21 deductions, First Schedule capital allowances, s.30 reliefs, s.58 Fourth Schedule tax). Skipped entirely (replaced with a one-line exemption notice) when `minimum_wage_exempt` is true — there's nothing to itemize below the minimum-wage threshold.

## 3. Itemized breakdown

Four sections — Income, Allowable Deductions, Capital Allowances, Statutory Reliefs — each a per-category table, omitted section-by-section when empty.

- **Income / Statutory Reliefs**: `Category | Amount` — a relief or income line either counts in full or it doesn't; there's no partial rate to show.
- **Allowable Deductions / Capital Allowances**: `Category | Gross Amount | Rate | Amount Deducted`. This is the piece that answers "what deduction rate applied, and how much did that come to":
  - **Rate = 100%** for a normal, fully-deductible business expense (software, internet, marketing, outsourcing — anything not touching a home office).
  - **Rate = the user's home-office percentage** (`user.home_office_percentage`, set once in Settings) for the one category that's genuinely split — Power & Workspace Utilities and the home-office share of rent. If a user works from home 30% of the time, only 30% of that utility bill is deductible; the report shows the full bill (**Gross Amount**), the 30% (**Rate**), and the resulting ₦ figure (**Amount Deducted**) side by side rather than only the net number, so the user can see *why* the deducted amount is smaller than what they actually paid.
  - **Capital allowances** show the asset's original **cost** as Gross Amount and its First Schedule class rate (Class 1 10%, Class 2 20%, Class 3 25%) as Rate — the yearly write-down, not the expense itself (a laptop's full price is never a same-year deduction; see `capital_allowances.py`).
  - Rate is computed as `amount_deducted / gross_amount * 100`, so it's always internally consistent with the two ₦ figures next to it — it is never a second, independently-entered number that could drift from the total.

## 4. Band-by-band computation

The Fourth Schedule progressive bands applied to Chargeable Income, each row showing the rate, how much income fell in that band, and the tax from that band alone — lets a user verify the Net Tax Payable figure by hand if they want to.

## 5. Disclaimer

A closing note that this is a self-assessment estimate, not a substitute for professional advice — matches the same posture as the AI Tax Advisor (`docs/SYSTEM_SPECIFICATION.md` §3.6).

## What this report deliberately does NOT include

- **Raw transaction listing.** The report is a computed summary, not a ledger export — the full transaction list lives in the app's Ledger page, not the PDF.
- **A hardcoded state filing portal link.** See `docs/filing_guidance/` — portal URLs change without notice, so the app only ever names a portal and points the user to search for it, never a baked-in address that can go stale.
- **Anything for a user with no APPROVED transactions in the requested year.** The PDF still generates (all-zero summary, "Records Covered: No approved records for this tax year yet") rather than failing — a user should always be able to download *something* for a year, even an empty one, to confirm the app registered no activity.

## Where to change something

| Want to change... | Edit |
|---|---|
| What appears in the header | `generator.py:build_report_pdf` (the `story` list's opening `Paragraph`s) |
| Which per-category fields the itemized tables carry | `reporting_helpers.py:build_itemized_breakdown` (deductions/income/reliefs) or `loader.py:load_capital_allowance_items` (capital allowances) |
| The actual tax math | `tax_computation/engine.py` and `capital_allowances.py` — never the report generator, which only *renders* an already-computed `TaxComputationResult` |
| The records-period calculation | `loader.py:get_records_period` |
