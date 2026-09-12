# Filing Guidance — Osun State

*Last researched: 2026-09-12. State filing portals, forms, and deadlines change — always confirm current details on the Osun Internal Revenue Service's (OIRS) official channels before filing.*

## Tax Authority

The **Osun Internal Revenue Service** (OIRS, sometimes rendered OSIRS) is the state agency responsible for assessing and collecting Personal Income Tax from Osun-resident taxpayers, including self-employed individuals, freelancers, and gig workers who meet the 183-day / principal-place-of-residence residency test for the state. Its official site is [irs.os.gov.ng](https://irs.os.gov.ng/).

## Registration & Taxpayer ID (TIN)

- OIRS issues a **Payer ID** on registration through its Main Revenue Portal, and separately supports TIN registration/verification integrated with the **Joint Tax Board (JTB)** national TIN system.
- **If you reside outside Osun State**, OIRS allows online registration to obtain a **Unique Payer Identification Number (PID)**, used for all subsequent payments and filings.
- **If you reside within Osun State**, the guidance found points residents toward visiting their closest Tax Station to register, rather than relying solely on the online form.
- An online Individual TIN Application form exists (via [irs.os.gov.ng](https://irs.os.gov.ng/) and a linked electronic-collections portal), which asks for personal details and a passport photo (JPG/PNG/JPEG, under 2MB) to build a taxpayer profile.
- *Not confirmed*: whether the online TIN/Payer ID registration form explicitly requires BVN or NIN as input fields — this was not visible in the page content retrieved. Have both on hand when registering, since BVN/NIN-linked identification is standard practice across Nigerian state revenue services.

## How to File Your Direct Assessment Return

OIRS separates annual filings into three categories: PAYE returns (for employees), **Direct Assessment (DA)** — for gross income that is not salary or business income with withholding already deducted — and Withholding Tax returns (director's fees, professional fees, contracts, royalties). A GigTax user, as a self-employed/freelance filer, files under Direct Assessment:

1. Register and obtain your Payer ID / TIN as described above.
2. Download the **Individual Tax Returns Template** (an MS Excel workbook) from the OIRS Downloads section on [irs.os.gov.ng](https://irs.os.gov.ng/downloads/).
3. Complete the template using your GigTax self-assessment figures: total gross income for the year, Section 20 allowable deductions (rent relief, tools of trade, data/telecoms, statutory contributions), net chargeable income, and computed tax payable under the NTA 2025 bands.
4. Submit the completed return either:
   - **Online**, through the submission form on the OIRS website, or
   - **By email**, sending only the completed MS Excel file as an attachment to irsosun2@gmail.com or irsosun@gmail.com (OIRS's own instructions state only the Excel file is required as an attachment — do not add extra documents unless asked).
   - A hard copy may also be required at an OIRS office in some cases; soft copies go to the OIRS site/email, hard copies to OIRS offices, per OIRS's own public notices.
5. Once your return is assessed, OIRS's self-assessment system lets a new taxpayer self-assess their liability, pay the calculated amount at a designated bank, and obtain an **electronic Tax Clearance Certificate (e-TCC)** without needing to visit a tax office in person.

## Filing Deadline

OIRS has publicly reaffirmed a **March 31** deadline for self-employed individuals to voluntarily file their annual tax returns for the preceding tax year, citing the Personal Income Tax Act 2004 (as amended). This mirrors the employer PAYE deadline of **January 31** for annual returns of employee emoluments. Failure to file by the self-employed deadline is stated to attract penalties and other statutory sanctions, though OIRS's published notice does not itemize the specific penalty amounts.

## Tax Clearance Certificate (TCC)

- Direct Assessment filers who self-assess and pay through a designated bank can obtain an e-TCC without an office visit, per OIRS's own description of the process.
- As with other states, a TCC typically needs three years of Direct Assessment returns/payments on record to be issued, covering the three years preceding the year of application.
- *Not confirmed*: exact processing/turnaround time for Osun's e-TCC specifically — check with OIRS directly (contact: info@oirs.ng or WhatsApp +234 818 969 7104, per the OIRS contact page).

## Sources

- [OIRS — Osun Internal Revenue Service (homepage)](https://irs.os.gov.ng/)
- [Individual Annual Tax Returns — Osun Internal Revenue Service](https://irs.os.gov.ng/individual-annual-tax-returns/) — filing categories, submission methods, required info
- [OSSG Reaffirms Deadline for Filing Annual Tax Returns — Osun Internal Revenue Service](https://irs.os.gov.ng/ossg-reaffirms-deadline-for-filing-annual-tax-returns/) — March 31 self-employed deadline, January 31 employer deadline, PITA 2004 basis
- [Individual TIN Application — Osun RMS](https://osun.electroniccollectionsecg.com/taxes/apply)
- [Contact us — Osun Internal Revenue Service](https://irs.os.gov.ng/contact-us/)
- [FAQs — Osun Internal Revenue Service](https://irs.os.gov.ng/faq/) (page content limited at time of research)

*Note: `https://irs.os.gov.ng` is stored as `portal_url` in `backend/db/seed_data/state_filing_portals.json` and linked directly in the app — confirmed live by direct fetch on 2026-09-12 (official OIRS homepage). If it ever stops working, search "OIRS Osun" for the current address.*
