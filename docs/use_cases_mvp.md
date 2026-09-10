# TaxEase NG: Use Case Document (MVP)

*Updated to align with the NTA 2025 Direct Assessment rules and current system architecture.*

## 1. System Overview
The system facilitates end-to-end tax compliance for Nigerian freelancers under the Direct Assessment regime. It acts as an AI-powered ledger, a BYOS (Bring Your Own Storage) document vault, and a tax planner, culminating in generating a Form A summary that users manually file on state portals (e.g., LIRS eTax, FCT-IRS).

## 2. Detailed Use Cases

### EPIC 1: Onboarding & Setup

**UC 1.1: Account Creation & Profiling**
*   **Actor:** Freelancer
*   **Description:** The user sets up their foundational tax profile to ensure compliance with correct state laws and deductions.
*   **Main Flow:**
    1.  User enters email and creates a secure password (stored securely via UUID).
    2.  User inputs Full Legal Name and Tax Identification Number (TIN).
    3.  User selects State of Residence (determines which SIRS gets jurisdiction, e.g., Lagos/LIRS).
    4.  User selects Sources of Income (Freelance, Digital Products).
    5.  User indicates Home Office Status (Yes/No). If Yes, they specify the percentage of their house used for work (e.g., 20%) to correctly apportion the NTA 2025 rent relief and utility deductions.
*   **Post-condition:** The user's dashboard is configured for their specific state portal and allowable reliefs.

**UC 1.2: Cloud Storage Integration (BYOS)**
*   **Actor:** Freelancer, Google Drive API
*   **Description:** The user connects their Google Drive to act as the primary storage vault for statements and receipts.
*   **Main Flow:**
    1.  User clicks "Connect Google Drive".
    2.  User authenticates via Google OAuth.
    3.  System creates a designated folder structure (e.g., `TaxEase Records/2026/`).

**UC 1.3: Set Natural Language Custom Rules**
*   **Actor:** Freelancer, AI Engine
*   **Description:** The user provides text-based instructions to guide the AI's transaction tagging.
*   **Main Flow:**
    1.  User navigates to Settings -> Custom Rules.
    2.  User types a rule (e.g., "My legal name is Favour Okafor, so any transfers from Favour are internal. Upwork payments are Gross Income.").
    3.  System saves the context into the `custom_rules` database table to feed into the AI Engine during the next upload.

---

### EPIC 2: Data Ingestion & Review

**UC 2.1: Upload Bank Statement**
*   **Actor:** Freelancer, AI Engine
*   **Description:** The user inputs their financial data into the system.
*   **Main Flow:**
    1.  User drags and drops a monthly Naira or Domiciliary bank statement (PDF or CSV).
    2.  System saves the file to the connected Google Drive and sends the text to the AI Engine.
    3.  AI applies NTA 2025 laws and the user's custom rules to classify rows into `IncomeRecord` or `ExpenseRecord`, assigning categories (e.g., Business - Rent, Personal, Gift) and converting foreign currency using prevailing CBN rates.

**UC 2.2: Manual Transaction Entry (Cash & Out-of-Bank)**
*   **Actor:** Freelancer
*   **Description:** The user manually logs a cash income or expense that did not pass through the bank statement.
*   **Main Flow:**
    1.  User clicks "Add Manual Transaction".
    2.  User fills out the form: Date, Amount, Description, and Category (Income or specific Expense subcategory).
    3.  User uploads a receipt if it is an expense.
    4.  System bypasses the AI engine and directly saves the transaction into the database, immediately updating the YTD metrics.
*   **Post-condition:** The transaction is added to the ledger without AI categorization.

**UC 2.3: Review & Approve Ledger (Human-in-the-Loop)**
*   **Actor:** Freelancer
*   **Description:** The user reviews the AI's tags for uploaded bank statements (to avoid the "Bank Inflow Audit Trap") and makes corrections.
*   **Main Flow:**
    1.  System presents a list of all parsed transactions with predicted subcategories.
    2.  User scrolls through the list. If a tag is wrong, the user selects the correct subcategory from a dropdown.
    3.  User clicks "Approve Statement" to lock the data into the database.
*   **Post-condition:** Dashboard YTD metrics update immediately based on the approved ledger.

---

### EPIC 3: Smart Deductions & Receipt Management

**UC 3.1: Handling the Dismissible Receipt Prompt**
*   **Actor:** Freelancer, Google Drive API
*   **Description:** The system encourages audit readiness for Section 20 allowable deductions without blocking workflow.
*   **Main Flow:**
    1.  User approves a transaction tagged as a deductible business expense (e.g., Software Subscriptions).
    2.  System triggers a UI prompt: "Upload receipt for this expense to ensure audit compliance."
    3.  **Alternate Flow A (Compliance):** User uploads a photo. System saves it to Google Drive, logs the URL in the `Receipt` table, and links it to the transaction.
    4.  **Alternate Flow B (Dismissal):** User clicks "Skip for now". The prompt closes, and the expense remains logged without a receipt.

**UC 3.2: Capital Allowances Routing**
*   **Actor:** System
*   **Description:** The system handles depreciation for hardware instead of expensing it directly in one year.
*   **Main Flow:**
    1.  User approves a transaction tagged as Business - Equipment/Hardware.
    2.  System flags this with `is_capital_allowance = True`.
    3.  System calculates the statutory depreciation percentage and deducts only that allowed percentage from the Assessable Profit for the current tax year.

---

### EPIC 4: AI Tax Advisor

**UC 4.1: Conversational Tax Advice**
*   **Actor:** Freelancer, AI Engine
*   **Description:** User gets instant, legally grounded answers to tax questions based on NTA 2025.
*   **Main Flow:**
    1.  User opens the AI Advisor chat widget.
    2.  User asks a question (e.g., "Is a new microphone deductible?").
    3.  AI responds strictly based on the RAG knowledge base of Nigerian tax laws. Chat history is saved in the `Advisory` table.

**UC 4.2: Tax Vault Planner**
*   **Actor:** System
*   **Description:** The system proactively tells the user how much cash to save for taxes to avoid year-end shock.
*   **Main Flow:**
    1.  User views the dashboard.
    2.  System calculates the live estimated tax liability by applying NTA 2025 progressive tax bands to the live Assessable Profit.
    3.  System displays a "Tax Vault" widget advising: "Based on YTD income, set aside ₦X in your personal savings for your tax bill."

---

### EPIC 5 & 6: Reporting, Filing & Compliance

**UC 5.1: Generate Annual Tax Report & Redirect**
*   **Actor:** Freelancer, State Tax Portal
*   **Description:** The user prepares to pay the government at year-end.
*   **Main Flow:**
    1.  User clicks "Generate Annual Report".
    2.  System compiles YTD Gross Income, Section 20 Deductions, Rent Relief, and Final Liability into a standardized summary (mimicking Form A).
    3.  User clicks "File My Taxes".
    4.  System redirects the user to their designated state portal (e.g., LIRS eTax) in a new tab to input the numbers and make the payment.

**UC 6.1: Tax Clearance Certificate (TCC) Upload**
*   **Actor:** Freelancer, Google Drive API
*   **Description:** The user logs their successful compliance.
*   **Main Flow:**
    1.  User returns to TaxEase after paying and receiving their e-TCC from the state portal.
    2.  User uploads the TCC document.
    3.  System saves it to Google Drive and links it to the `Tax` table for that year.
    4.  System closes the tax year and resets the Estimated Tax Liability for the new year to ₦0.
