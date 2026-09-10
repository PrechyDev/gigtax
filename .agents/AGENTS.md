# AI Categorization Service Architecture and Rules

## Overview
This document defines the rules and architecture for the AI Categorization Service. It must be consulted by any agent working on this module to ensure consistency.

## Tech Stack
- **Backend Framework**: Python (FastAPI)
- **Database**: PostgreSQL with SQLAlchemy (via docker)
- **Dependency Management**: Poetry
- **Data Parsing**: `pandas` (for CSV/Excel), `pdfplumber` (for PDFs), with fallback to `llama-parse` and Gemini.
- **PII Sanitization**: Microsoft Presidio (`presidio-analyzer`, `presidio-anonymizer`)
- **LLM Routing/Structured Output**: `instructor` with `litellm` (via docker)
- **Default LLM**: Gemini Flash 3.5

## Key Principles
1. **Security First (PII Scrubbing)**: All documents MUST pass through the PII sanitizer before any text is sent to an external LLM. In-memory processing only. Do not persist user bank statements.
2. **Avoid Overengineering**: Keep modules decoupled but simple. Test each piece independently.
3. **Graceful Fallbacks**: Extractors should attempt local parsing first (pandas/pdfplumber) before falling back to LlamaParse/Gemini to reduce cost and latency.

## Architecture Guidelines
- **`services/parsing.py`**: Handles all extraction logic. Takes bytes/file object, returns raw text. If a PDF is password protected, it will raise `PasswordRequiredError`.
- **`services/sanitization.py`**: Handles PII redaction. Takes raw text, returns sanitized text.
- **`services/categorization.py`**: Applies custom user rules and assigns categories using LLM reasoning. Takes sanitized text and rules, returns typed Pydantic models mapping to `Transaction` DB schema.
- **`services/llm_service.py`**: Centralized LLM facade. Implements automatic rate limit (HTTP 429) fallback cascading (`3.6-flash` -> `2.5-flash` -> `3.5-flash-lite`) to prioritize latency over retries.

## API & Frontend Integration Notes
- **Locked PDFs (Passwords)**: When building the FastAPI endpoints, if `parsing.py` raises a `PasswordRequiredError`, the API MUST return an `HTTP 423 Locked` response. The Frontend should catch this 423 status, prompt the user for the password in a modal, and re-submit the request with the `password` field included. Passwords MUST be kept strictly in RAM and never logged.
