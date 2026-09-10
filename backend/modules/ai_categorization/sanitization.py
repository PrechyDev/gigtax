import re
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine

# Lazy loading variables
_analyzer = None
_anonymizer = None

def setup_custom_recognizers(analyzer: AnalyzerEngine):
    # Nigerian Location Recognizer (Case insensitive)
    nigerian_locations = [
        "ABIA", "ADAMAWA", "AKWA IBOM", "ANAMBRA", "BAUCHI", "BAYELSA", "BENUE", "BORNO", 
        "CROSS RIVER", "DELTA", "EBONYI", "EDO", "EKITI", "ENUGU", "GOMBE", "IMO", "JIGAWA", 
        "KADUNA", "KANO", "KATSINA", "KEBBI", "KOGI", "KWARA", "LAGOS", "NASARAWA", "NIGER", 
        "OGUN", "ONDO", "OSUN", "OYO", "PLATEAU", "RIVERS", "SOKOTO", "TARABA", "YOBE", 
        "ZAMFARA", "FCT", "ABUJA", "NIGERIA", "IFE CENTRAL", "PORT HARCOURT", "IBADAN"
    ]
    loc_regex = r"(?i)\b(?:" + "|".join(nigerian_locations) + r")\b"
    loc_pattern = Pattern(name="nigerian_location_pattern", regex=loc_regex, score=0.85)
    # The user noted: "for address you's usually see address written before it"
    loc_recognizer = PatternRecognizer(supported_entity="LOCATION", patterns=[loc_pattern], context=["address", "location", "street", "city", "state"])
    analyzer.registry.add_recognizer(loc_recognizer)

    # Caps Name Recognizer (2 to 4 ALL CAPS words)
    name_regex = r"\b[A-Z]{3,} [A-Z]{3,}(?: [A-Z]{3,})?\b"
    name_pattern = Pattern(name="caps_name_pattern", regex=name_regex, score=0.7)
    name_recognizer = PatternRecognizer(supported_entity="PERSON", patterns=[name_pattern], context=["name", "customer", "account", "mr", "mrs"])
    analyzer.registry.add_recognizer(name_recognizer)

def get_analyzer():
    global _analyzer
    if _analyzer is None:
        print("Loading Presidio NLP model into memory (this takes a moment)...")
        _analyzer = AnalyzerEngine()
        setup_custom_recognizers(_analyzer)
    return _analyzer

def get_anonymizer():
    global _anonymizer
    if _anonymizer is None:
        _anonymizer = AnonymizerEngine()
    return _anonymizer

def sanitize_text(text: str, language: str = "en") -> str:
    """
    Analyzes the text for PII and redacts them.
    Splits into Header (aggressive scrubbing) and Transactions (light scrubbing to preserve merchants).
    """
    if not text:
        return text

    analyzer = get_analyzer()
    anonymizer = get_anonymizer()

    # Heuristic split: first 1500 chars are usually the header/profile section.
    split_index = 1500
    
    # If we find "Opening Balance" or similar, use that as a dynamic split point
    match = re.search(r"(?i)(Opening Balance|Transaction History|Date\s+Description)", text)
    if match:
        # Give it a 200 char buffer after the keyword to capture the table headers safely
        split_index = min(len(text), match.end() + 200)

    if len(text) > split_index:
        header_text = text[:split_index]
        transaction_text = text[split_index:]
    else:
        header_text = text
        transaction_text = ""

    # 1. Aggressive Header Scrubbing
    header_results = analyzer.analyze(text=header_text,
                               entities=["PERSON", "LOCATION", "PHONE_NUMBER", "EMAIL_ADDRESS", "CREDIT_CARD", "IBAN_CODE", "IP_ADDRESS"],
                               language=language)
    header_sanitized = anonymizer.anonymize(text=header_text, analyzer_results=header_results).text

    # 2. Light Transaction Scrubbing (Preserve PERSON and LOCATION for merchants)
    if transaction_text:
        trans_results = analyzer.analyze(text=transaction_text,
                                   entities=["PHONE_NUMBER", "EMAIL_ADDRESS", "CREDIT_CARD", "IBAN_CODE", "IP_ADDRESS"],
                                   language=language)
        trans_sanitized = anonymizer.anonymize(text=transaction_text, analyzer_results=trans_results).text
    else:
        trans_sanitized = ""

    return header_sanitized + trans_sanitized
