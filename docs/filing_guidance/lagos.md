# Filing Guidance — Lagos State

*Last researched: 2026-09-12. State filing portals, forms, and deadlines change — always confirm current details on LIRS's official channels before filing.*

## Tax Authority

The **Lagos State Internal Revenue Service (LIRS)** administers Personal Income Tax for individuals resident in Lagos State. Lagos has the largest concentration of freelancers, remote tech workers, and creative-economy taxpayers in the country, and LIRS runs the most digitized state filing system in Nigeria.

## Registration & Taxpayer ID (TIN)

Registration is done through the **eTax portal** and requires your **Bank Verification Number (BVN)** and **National Identification Number (NIN)**. Once verified, LIRS issues a unique **LIRS Taxpayer ID (Payer ID)**, which doubles as your state TIN for Lagos filing purposes. If you don't already have a Payer ID, register on the portal before your first filing — you cannot file a Direct Assessment return without one.

## How to File Your Direct Assessment Return

LIRS's **eTax Portal** (search "LIRS eTax" for the current official link — etax.lirs.net at time of writing) handles Direct Assessment self-assessment filing end to end:

1. Log in to eTax with your Payer ID and password.
2. Navigate to **"File Annual Returns"** (Form A self-assessment, the standard Direct Assessment form under the Nigeria Tax Act 2025).
3. Enter your **total gross income** for the tax year — this is the "Total Income" figure from your GigTax report, including any foreign-currency income already converted to Naira.
4. Enter your **allowable deductions** (Section 20 business expenses) and **statutory reliefs** (Section 30) — use the itemized "Allowable Deductions", "Capital Allowances", and "Statutory Reliefs" breakdowns from your GigTax report line by line, and attach a copy of the GigTax report itself as your supporting Statement of Income & Expenditure.
5. Upload your 12-month bank statements, invoices, and payment receipts as supporting evidence.
6. Submit. The portal applies the NTA 2025 progressive bands automatically and generates an **Assessment Notice** with a payment reference (Bill Reference) — this should match (or closely track) the "Net Tax Payable" figure GigTax computed for you. If the two numbers diverge significantly, double-check your entries before paying.
7. Pay via the integrated channels: Quickteller, WebPAY, or direct bank transfer, using the Bill Reference.

## Filing Deadline

**March 31** annually, for the preceding tax year (e.g. the 2026 tax year return is due by March 31, 2027).

## Tax Clearance Certificate (TCC)

Once LIRS confirms full payment against your assessment, an electronic **Tax Clearance Certificate (e-TCC)** becomes downloadable directly from your eTax dashboard. No separate application is needed.

## Sources

- LIRS eTax Portal (etax.lirs.net) — portal name and workflow as described in project research notes (`docs/nta_2025_research.md`), compiled 2026-09.
- Nigeria Tax Act 2025 (Sections 20, 30, 41, 58) — federal framework underlying the state's Form A computation; see `docs/nta_2025_research.md` for the full band table.

*Note: `https://etax.lirs.net` is stored as `portal_url` in `backend/db/seed_data/state_filing_portals.json` and linked directly in the app. It returned an HTTP 403 on a direct automated fetch (2026-09-12) — consistent with anti-bot protection on a login page rather than a dead link, and it matches the address independently named in project research — but this wasn't visually confirmed the way the FCT/Oyo/Osun portals were. If it ever stops working, search "LIRS eTax" for the current address.*
