# Contributor Guide

Welcome to the GigTax project! We are thrilled that you are interested in contributing. This document outlines the process for contributing, our architectural standards, and how to get your development environment set up properly.

## 🤝 How to Contribute

1. **Fork the Repository**: Create your own fork of the repository.
2. **Create a Branch**: Create a feature branch from `main` (e.g., `feature/awesome-new-advisory-tool` or `fix/auth-token-leak`).
3. **Commit your Changes**: Write clear, descriptive commit messages.
4. **Push to the Branch**: Push your changes to your fork.
5. **Open a Pull Request**: Submit a Pull Request targeting the `main` branch. Provide a detailed description of what you changed and why.

## 🏛 Architecture Overview

Before making changes, it is important to understand the system architecture to ensure your contributions align with our design philosophy.

- **Backend**: Built with **FastAPI** and **Python 3.10+**. 
  - **Statelessness**: The backend is completely stateless. We use JWTs for authentication.
  - **Database**: PostgreSQL handled via **SQLAlchemy** ORM and **Alembic** for migrations.
  - **AI Integration**: We use `litellm` and `instructor` in `services/llm_service.py` to wrap Google Gemini models. This service handles transient errors (429s, 503s) with exponential backoff and fallback cascades. Please use this service rather than making raw API calls.
  - **Security**: Be very careful with OAuth states and JWTs. We use purpose-scoped JWTs for things like Google Drive OAuth (`create_oauth_state_token`) to prevent token leakage.
- **Frontend**: A modern React application built with **Vite** and styled with **Tailwind CSS**. 
- **Storage (BYOS)**: We do not host user files centrally. Instead, we use a "Bring Your Own Storage" model. Documents are saved directly to the user's connected Google Drive.

## 💻 Development Setup

Please refer to the `Local Development Setup` section in our main [README.md](README.md) for step-by-step instructions on setting up Docker, Postgres, the Backend (via `poetry`), and the Frontend (via `npm`).

### Testing Requirements

We enforce testing to maintain stability, especially around tax calculations and AI data extraction.
- **Backend Tests**: Run `poetry run pytest` from the `/backend` directory. 
- **Mocking**: No automated test in our suite makes a real Gemini API call. All LLM calls must be mocked during testing. If you add a new AI-driven feature, ensure you provide mock responses in your tests.
- **Manual Pipeline**: For real LLM validation, use the manual pipeline check (`backend/test_pipeline.py <file_path>`). This is strictly opt-in and is never run in CI.

## 🐛 Reporting Bugs

If you find a bug, please open an Issue with:
1. A clear title and description.
2. Steps to reproduce the issue.
3. The expected vs. actual behavior.
4. Any relevant logs or screenshots (please redact sensitive API keys or personal data).

## 🛡 Security Vulnerabilities

If you discover a security vulnerability (e.g., IDOR, SQL injection, token leakage), **do not open a public issue**. Please reach out to the project maintainers directly via email so we can patch it responsibly before disclosure.

---
Thank you for helping make GigTax better for everyone!
