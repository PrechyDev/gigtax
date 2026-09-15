# GigTax

GigTax is an AI-powered tax assessment and reporting system designed specifically for Nigerian self-reporting taxpayers (freelancers, gig workers, and small business owners) under the **Nigeria Tax Act 2025**. 

The system leverages Generative AI to automate the categorization of raw bank transactions, calculate allowable deductions (including complex rules like Home Office usage), and provide actionable, context-aware tax advisory.

## 🚀 Key Features
- **AI-Powered Categorization**: Upload raw CSV bank statements and let AI automatically categorize your income and expenses according to Nigerian tax laws.
- **Dynamic Tax Computation**: Real-time calculation of your tax liability, with dynamic support for prorated deductions (e.g., Home Office percentage).
- **Bring Your Own Storage (BYOS)**: We prioritize your privacy. Connect your personal Google Drive, and GigTax will securely store your processed financial documents directly in your own cloud account.
- **Smart Advisory**: Chat with an AI assistant that understands your financial data and can answer specific questions about your tax profile.
- **Document Generation**: Automatically generate and export formatted tax computation sheets ready for filing.

## 🛠 Tech Stack
- **Backend**: Python, FastAPI, SQLAlchemy, PostgreSQL, Alembic
- **Frontend**: Node, React/Vite, Tailwind CSS
- **AI/LLM**: Google Gemini (via `litellm` and `instructor` for structured outputs)
- **Infrastructure**: Docker, Render (Backend), Vercel (Frontend), Neon (Postgres)

---

## 📖 How to Use the Application

### 1. Complete Your Profile & Add Custom Rules
After registering an account, your first step is to complete your annual tax profile (e.g., configuring your state of residence, tax year, and home office deductibility percentage). You can also define **Custom Rules** to instruct the AI on how to handle specific merchants or transaction patterns unique to your business.

### 2. Connect Your Drive (Optional)
If you want to use our "Bring Your Own Storage" feature, navigate to the settings and connect your **Google Drive**. This authorizes the application to create a dedicated GigTax folder in your drive where all your statements and computation reports will be safely stored. If you skip this, the app still works, but documents won't be persistently synced to the cloud.

### 3. Upload Bank Statements
Navigate to the Statements dashboard and upload your bank statement (CSV format). The system will process the raw rows and pass them to our AI categorization engine.

### 4. Review and Recategorize
The AI will tag each transaction (e.g., "Software Subscriptions", "Utilities", "Professional Fees"). You can manually review these categorizations on the Transactions page. Any changes you make will be remembered for future statements.

### 5. Compute Tax Liability
Once your transactions are finalized, visit the Tax Computation page. Hit "Compute" to calculate your total taxable income, total allowable deductions, and final estimated tax liability based on the latest tax brackets.

### 6. Chat for Advisory
Have a question about a specific deduction? Open the Advisory chat panel. The AI assistant has context on your recent transactions and tax profile, providing personalized advice.

---

## 💻 Local Development Setup

### Prerequisites
- Node.js (v18+)
- Python (3.10+) with `poetry` installed
- Docker (for local PostgreSQL)
- Google Cloud Console Account (for Drive API credentials)
- Gemini API Key

### Quick Start (Windows)
We provide bundled PowerShell scripts to quickly spin up the entire stack.
```powershell
.\start-dev.ps1   # Starts Postgres in Docker, runs Alembic migrations, and launches both backend + frontend
.\stop-dev.ps1    # Stops all services safely (Postgres data is preserved)
```
*Note: You must create a `backend/.env` file with your API secrets before starting. See `.env.example` in the backend folder.*

### Manual Setup (macOS / Linux)

**1. Start the Database**
```bash
docker compose up -d db
```

**2. Setup Backend**
```bash
cd backend
poetry install
cp .env.example .env             # Fill in your GEMINI_API_KEY, JWT_SECRET, etc.
poetry run alembic upgrade head  # Runs DB migrations and seeds categories
poetry run uvicorn main:app --reload
```
API Documentation will be available at: http://localhost:8000/docs

**3. Setup Frontend**
```bash
cd frontend
npm install
npm run dev -- --port 5173
```
Frontend will be available at: http://localhost:5173

---

## 🤝 Contributing

We welcome contributions from the community! Whether it's reporting a bug, proposing a new feature, or submitting a Pull Request.

Please read our [Contributor Guide](contributor.md) for details on our code of conduct, architectural overview, and the process for submitting pull requests to us.

---

## 📄 Further Documentation
- [`docs/SYSTEM_SPECIFICATION.md`](docs/SYSTEM_SPECIFICATION.md): Full feature specification.
- [`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md): Architectural decisions and build plan.
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md): Step-by-step production deployment guide.
