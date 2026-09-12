# State Filing Guidance

Self-reporter filing guides for GigTax users — how to take the numbers on your GigTax self-assessment report and actually file them with your **State Internal Revenue Service**. The Nigeria Tax Act 2025 sets the federal computation (progressive bands, Section 20 deductions, Section 30 reliefs — see `docs/nta_2025_research.md`), but *filing* is administered separately by each state, so the process, portal, and deadline details differ.

| State | File | Digital portal? | Linked in app? |
|---|---|---|---|
| Lagos | [lagos.md](lagos.md) | Yes — LIRS eTax, mature/fully online | Yes (`etax.lirs.net`) |
| FCT (Abuja) | [fct_abuja.md](fct_abuja.md) | Yes — FCT-IRS Taxportal, mature/fully online | Yes (`fcttaxportal.fctirs.gov.ng`) |
| Rivers | [rivers.md](rivers.md) | Yes — RIVTAMIS, mature/fully online | Yes (`rivtamis.riversbirs.gov.ng`) |
| Oyo | [oyo.md](oyo.md) | Partial — OYSBIR self-service portal + in-person/paper route | Yes (`selfservice.oyostatebir.com`) |
| Osun | [osun.md](osun.md) | Partial — OIRS Excel template, submitted online or by email | Yes (`irs.os.gov.ng`) |
| Ogun | [ogun.md](ogun.md) | Partial — OGIRS portal(s); canonical URL unconfirmed, see file | No — no confirmed live portal |

## How these were produced

Lagos, FCT, and Rivers were researched first and are documented in more depth in `docs/nta_2025_research.md`; these three files summarize that same research in the self-reporter format below. Oyo, Osun, and Ogun were researched separately (2026-09-12) directly against each state's own revenue service site, and are more forthright about what wasn't confirmable from public sources — do not read the shorter "Sources" list on those three as less real, it reflects genuinely thinner public documentation for those states, not less effort.

## Shared structure

Each file follows the same shape: **Tax Authority** (who administers PIT there), **Registration & Taxpayer ID (TIN)** (what you need and what ID you get), **How to File Your Direct Assessment Return** (concrete numbered steps, phrased around the GigTax report's own figures — total income, allowable deductions, capital allowances, statutory reliefs, net tax payable), **Filing Deadline**, **Tax Clearance Certificate (TCC)**, and **Sources**.

## Important caveats

- **Portal URLs are only stored in the app (`backend/db/seed_data/state_filing_portals.json`) once directly fetched and visually confirmed live** — never guessed from a title or a search result. 5 of the 6 states above have a confirmed URL and a working "Go to portal" link in the app; Ogun does not, because the only candidate address found shows signs of being stale (see `ogun.md`) and no canonical portal could be confirmed. Government portal addresses can still move without notice even after being confirmed once — re-verify before treating any of these as permanent.
- Where a fact could not be confirmed from a primary source (an exact deadline, whether BVN/NIN is required at registration, TCC turnaround time), the relevant file says so explicitly rather than presenting a guess as fact. Always confirm current details with the state's own revenue service before filing.
- These guides cover **Direct Assessment (self-assessment) for self-employed individuals** only — the regime GigTax's target users (freelancers, remote workers, creators, digital vendors) file under. They do not cover PAYE, companies/CIT, or VAT.
- Only 6 of Nigeria's 36 states + FCT are covered here. `GET /filing-guidance` in the app falls back to generic guidance (pointing the user to search for their own state's SIRS) for any state not in this list.
