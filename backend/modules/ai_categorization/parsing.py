import pandas as pd
import pdfplumber
import pymupdf
import io
import os
from typing import Optional

class ParsingError(Exception):
    pass

class PasswordRequiredError(Exception):
    pass

def parse_csv(file_bytes: bytes) -> str:
    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
        return df.to_string(index=False)
    except Exception as e:
        raise ParsingError(f"Failed to parse CSV: {e}")

def parse_excel(file_bytes: bytes) -> str:
    try:
        df = pd.read_excel(io.BytesIO(file_bytes))
        return df.to_string(index=False)
    except Exception as e:
        raise ParsingError(f"Failed to parse Excel: {e}")

def parse_pdf_pdfplumber(file_bytes: bytes, password: Optional[str] = None) -> str:
    try:
        text = ""
        with pdfplumber.open(io.BytesIO(file_bytes), password=password) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        if len(text.strip()) < 100:
            raise ParsingError("Extracted text is too short (likely just headers/footers in a scanned image).")
        return text
    except Exception as e:
        error_msg = str(e).lower()
        if "password" in error_msg or "encrypt" in error_msg:
            raise PasswordRequiredError("PDF is password protected or password was incorrect.")
        raise ParsingError(f"pdfplumber failed: {e}")

def parse_pdf_pymupdf(file_bytes: bytes, password: Optional[str] = None) -> str:
    try:
        text = ""
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        
        if doc.needs_pass:
            if not password or not doc.authenticate(password):
                raise PasswordRequiredError("PDF is password protected or password was incorrect.")
                
        for page in doc:
            page_text = page.get_text()
            if page_text:
                text += page_text + "\n"
        if len(text.strip()) < 100:
            raise ParsingError("Extracted text is too short (likely just headers/footers in a scanned image).")
        return text
    except PasswordRequiredError:
        raise
    except Exception as e:
        raise ParsingError(f"PyMuPDF failed: {e}")

def parse_with_gemini(file_bytes: bytes, mime_type: str = "application/pdf") -> str:
    """For scanned/complex PDFs: assumes the source is a tabular bank statement."""
    from services.llm_service import llm_service
    try:
        print("Extracting tabular data with LiteLLM Vision (gemini-3.5-flash fallback)...")
        prompt = (
            "Extract all the text and tabular data from this document perfectly. "
            "Maintain column alignment and make sure numbers and descriptions are completely accurate. "
            "CRITICAL SECURITY REQUIREMENT: You MUST redact all Personally Identifiable Information (PII) before returning the text. "
            "You are strictly forbidden from outputting the customer's name, physical address, phone numbers, or email addresses. "
            "Replace every single occurrence of a person's address, phone number or account number with the exact string '<REDACTED>, leaving names in transaction details and using those to mape income_source or merchant_name'."
        )

        text = llm_service.generate_vision_text(
            prompt=prompt,
            system_prompt="You are a precise financial data extraction AI. Follow all extraction and security instructions perfectly.",
            file_bytes=file_bytes,
            mime_type=mime_type
        )

        if not text:
            raise ParsingError("LLM returned empty text.")
        return text
    except Exception as e:
        raise ParsingError(f"LiteLLM extraction failed: {e}")


def parse_image_with_gemini(file_bytes: bytes, mime_type: str) -> str:
    """For photos of handwritten/freeform income-expense notes (not a tabular statement).

    There is no reliable local-OCR path for handwriting — Tesseract was tried and
    abandoned on this project for hallucinating digits on real documents (see
    docs/ai_categorization_architecture.md) — so every image goes straight here,
    with a prompt tuned for loose/freeform notes rather than aligned table columns.
    """
    from services.llm_service import llm_service
    try:
        print("Extracting handwritten/freeform notes with Gemini Vision...")
        prompt = (
            "This image contains a handwritten or informally typed note listing income and/or "
            "expense entries — it may not be a neat table. Read every entry you can make out and "
            "output them as plain text lines, one entry per line, in the form: "
            "`<date if present> - <description> - <amount>`. "
            "If a date isn't written for an entry, omit it rather than guessing. "
            "Do not skip entries because the handwriting is unclear — give your best reading rather "
            "than omitting a line; never invent entries that aren't there. "
            "CRITICAL SECURITY REQUIREMENT: redact all Personally Identifiable Information (PII) — "
            "replace any physical address, phone number, or account number with the exact string "
            "'<REDACTED>'. Names of people/businesses in a transaction description may stay, since "
            "they're needed to identify the income source or merchant."
        )

        text = llm_service.generate_vision_text(
            prompt=prompt,
            system_prompt="You are a precise financial data extraction AI reading a handwritten note. Follow all extraction and security instructions perfectly.",
            file_bytes=file_bytes,
            mime_type=mime_type,
        )

        if not text:
            raise ParsingError("LLM returned empty text.")
        return text
    except Exception as e:
        raise ParsingError(f"Gemini image extraction failed: {e}")


IMAGE_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def extract_text(file_bytes: bytes, filename: str, password: Optional[str] = None) -> str:
    """
    Main entry point for extracting text from a file.
    Tries fast local methods first, then falls back to cloud AI.
    Images have no local-parsing path and go straight to Gemini Vision.
    """
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".csv":
        return parse_csv(file_bytes)

    elif ext in [".xls", ".xlsx"]:
        return parse_excel(file_bytes)

    elif ext in IMAGE_MIME_TYPES:
        return parse_image_with_gemini(file_bytes, mime_type=IMAGE_MIME_TYPES[ext])

    elif ext == ".pdf":
        # 1. Try pdfplumber
        try:
            print("Attempting pdfplumber extraction...")
            return parse_pdf_pdfplumber(file_bytes, password)
        except PasswordRequiredError:
            raise
        except ParsingError:
            pass

        # 2. Try PyMuPDF
        try:
            print("Attempting PyMuPDF extraction...")
            return parse_pdf_pymupdf(file_bytes, password)
        except PasswordRequiredError:
            raise
        except ParsingError:
            pass

        # 3. Fallback directly to Gemini for complex scanned tables
        print("Local text extraction failed. Attempting Gemini API...")
        return parse_with_gemini(file_bytes, mime_type="application/pdf")

    raise ParsingError(f"Unsupported file format: {ext}")
