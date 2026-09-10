import asyncio
import os
import sys
from dotenv import load_dotenv
from modules.ai_categorization.parsing import extract_text, PasswordRequiredError
from modules.ai_categorization.sanitization import sanitize_text
from modules.ai_categorization.categorization import categorize_transactions

# Load environment variables
load_dotenv()

def run_test():
    if len(sys.argv) < 2:
        print("Usage: python test_pipeline.py <file_path>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        print(f"Loaded file: {file_path}")
    else:
        print(f"File not found: {file_path}")
        return

    custom_rules = """
    1. Ignore any bank charges under 100 naira.
    2. Treat anything from 'Uber' as Travel.
    3. If a transaction is an internal transfer or loan to 'Precious Robinson Okafor', 'myself', or '<REDACTED>', classify it as 'uncategorized'.
    4. If a transaction is for 'stamp duty', ignor it.
    """
    
    predefined_categories = """
    - developer_slug: exp_software_subscriptions (Software & Subscriptions)
    - developer_slug: exp_internet_data (Internet & Communication)
    - developer_slug: freelance_gig_fees (Professional Gig Fees)
    - developer_slug: exp_travel (Travel)
    """

    print("\n==============================")
    print("PHASE 1: EXTRACTION (PARSING)")
    print("==============================")
    try:
        raw_text = extract_text(file_bytes=file_bytes, filename=file_path)
    except PasswordRequiredError:
        print("\n[LOCKED] This PDF requires a password.")
        pwd = input("Enter PDF password: ").strip()
        raw_text = extract_text(file_bytes=file_bytes, filename=file_path, password=pwd)

    print(f"Extracted {len(raw_text)} characters.\n")
    print("--- RAW TEXT PREVIEW (First 500 chars) ---")
    print(raw_text[:500])
    print("------------------------------------------")
    
    # If the text is empty, the PDF might be an image without OCR
    if not raw_text.strip():
        print("CRITICAL ERROR: No text was extracted. The PDF is empty or needs OCR.")
        return

    print("\n==============================")
    print("PHASE 2: SANITIZATION (SECURITY)")
    print("==============================")
    sanitized_text = sanitize_text(raw_text)
    print(f"Sanitized down to {len(sanitized_text)} characters.\n")
    print("--- SANITIZED TEXT PREVIEW (First 500 chars) ---")
    print(sanitized_text[:1000])
    print("------------------------------------------------")

    print("\n==============================")
    print("PHASE 3: AI CATEGORIZATION (LLM)")
    print("==============================")
    transactions = categorize_transactions(
        sanitized_text=sanitized_text,
        custom_rules=custom_rules,
        predefined_categories=predefined_categories
    )
    
    print(f"\nAI found {len(transactions)} transactions.")
    for t in transactions:
        print(t.model_dump_json(indent=2))

if __name__ == "__main__":
    run_test()
