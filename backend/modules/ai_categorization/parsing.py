import pandas as pd
import pdfplumber
import pymupdf
import pytesseract
from PIL import Image
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

def extract_text(file_bytes: bytes, filename: str, password: Optional[str] = None) -> str:
    """
    Main entry point for extracting text from a file.
    Tries fast local methods first, then falls back to cloud AI.
    """
    ext = os.path.splitext(filename)[1].lower()
    
    if ext == ".csv":
        return parse_csv(file_bytes)
            
    elif ext in [".xls", ".xlsx"]:
        return parse_excel(file_bytes)
            
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
        return parse_with_gemini(file_bytes)
    
    raise ParsingError(f"Unsupported file format: {ext}")
