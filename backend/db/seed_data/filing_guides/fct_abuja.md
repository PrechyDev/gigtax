# Filing Guidance — FCT (Abuja)

*Last researched: 2026-09-12. State filing portals, forms, and deadlines change — always confirm current details on FCT-IRS's official channels before filing.*

## Tax Authority

The **Federal Capital Territory Internal Revenue Service (FCT-IRS)** administers Personal Income Tax for individuals resident in Abuja and the surrounding FCT satellite towns. FCT-IRS is treated as a state-level revenue authority for Direct Assessment purposes, even though the FCT itself is not a state.

## Registration & Taxpayer ID (TIN)

Registration is completed on the **FCT-IRS Self Service Portal** using **BVN/NIN** verification, which generates your **FCT Tax Identification Number (TIN)**. This TIN is required before you can file a Direct Assessment return.

## How to File Your Direct Assessment Return

The **FCT-IRS Taxportal** (search "FCT-IRS Taxportal" for the current official link — fcttaxportal.fctirs.gov.ng at time of writing) handles filing:

1. Log in to the portal dashboard and select **Tax Returns → File a New Return**.
2. Generate a **Returns Reference Number (RRN)** for the assessment year you're filing.
3. Complete the digitized **Form A**, in its four parts:
   - Part A: income
   - Part B: allowable deductions
   - Part C: dependents/rent relief
   - Part D: net chargeable income
   Use the "Total Income", "Allowable Deductions", "Capital Allowances", and "Statutory Reliefs" figures from your GigTax report to fill these in, section by section.
4. If any client withheld tax at source (Withholding Tax, WHT), declare the WHT credit and upload the WHT credit note — this offsets your PIT liability directly.
5. Upload your bank statements and expense proof documents.
6. Submit for automated self-assessment calculation. The system-generated tax figure should track your GigTax "Net Tax Payable" number; check both if they diverge before paying.
7. Pay via **Remita** or the FCT-IRS payment gateway using the reference generated.

FCT-IRS enforces this closely for Abuja-based remote workers who later need a TCC for government services — passport renewal, land allocation, and similar processes typically require one.

## Filing Deadline

Annual Direct Assessment returns follow the same national **March 31** filing deadline used across Nigeria's state revenue authorities, for the preceding tax year. Confirm on the FCT-IRS portal each year, as deadlines can be extended by public notice.

## Tax Clearance Certificate (TCC)

Issued through the FCT-IRS Taxportal once your return and payment are confirmed. Required for several downstream government services in the FCT (land allocation, passport renewal, government contract bidding), so it is worth requesting even if you don't need it immediately.

## Sources

- FCT-IRS Self Service Portal (fcttaxportal.fctirs.gov.ng) — portal name and workflow as described in project research notes (`docs/nta_2025_research.md`), compiled 2026-09.
- Nigeria Tax Act 2025 (Sections 20, 27, 30, 58) — federal framework underlying Form A; see `docs/nta_2025_research.md` for the full band table.

*Note: `https://fcttaxportal.fctirs.gov.ng` is stored as `portal_url` in `backend/db/seed_data/state_filing_portals.json` and linked directly in the app — confirmed live by direct fetch on 2026-09-12 (loaded the real FCT-IRS E-Tax login/session page). If it ever stops working, search "FCT-IRS Taxportal" for the current address.*
