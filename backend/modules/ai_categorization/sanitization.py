import re
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_analyzer.nlp_engine import NlpEngineProvider
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
        # Presidio's AnalyzerEngine() defaults to spaCy's "lg" model if not told
        # otherwise — its word vectors alone use several hundred MB once loaded,
        # which reliably OOMs a 512MB-RAM Render free-tier instance (confirmed: the
        # deployed app hit exactly this and stopped responding to everything, not
        # just statement uploads). "sm" costs some PERSON/LOCATION detection
        # accuracy, but format-based redaction (phone, email, card, IBAN — see
        # ALWAYS_REDACTED_ENTITIES below) is regex-based and doesn't depend on the
        # NLP model at all, so the highest-risk PII categories are unaffected.
        nlp_engine = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        }).create_engine()
        _analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
        setup_custom_recognizers(_analyzer)
    return _analyzer

def get_anonymizer():
    global _anonymizer
    if _anonymizer is None:
        _anonymizer = AnonymizerEngine()
    return _anonymizer


# Format-based entities are unambiguous — safe to redact anywhere in the document,
# transaction lines included, with no false-positive risk.
ALWAYS_REDACTED_ENTITIES = ["PHONE_NUMBER", "EMAIL_ADDRESS", "CREDIT_CARD", "IBAN_CODE", "IP_ADDRESS"]

# PERSON/LOCATION detection is far less precise — spaCy's NER routinely mistakes an
# ordinary capitalized business or product name ("Canva Pro", "GitHub", "Data
# subscription") for a person or place. A blind character-offset split used to run this
# over the whole document (or the whole thing, if no split point was found at all —
# exactly what corrupted real transaction descriptions in practice). Instead, only scan
# the short span right after an explicit account-holder label, the one place a real
# name/address is actually expected to appear.
ACCOUNT_HOLDER_LABEL_PATTERN = re.compile(
    r"(?i)\b(?:Account\s*Name|Account\s*Holder|Customer\s*Name|Customer)\s*[:\-]\s*"
)
# Enough characters after the label to cover a name/address, not so many that the scan
# drifts into an unrelated later line.
LABEL_WINDOW_CHARS = 120


def sanitize_text(text: str, language: str = "en") -> str:
    """
    Redacts PII from extracted statement text before it reaches an LLM.

    Phone numbers, emails, card numbers, IBANs, and IP addresses are redacted
    everywhere — they're unambiguous, format-based patterns. Person names and
    locations are only redacted within a short window immediately following an
    explicit account-holder label (e.g. "Account Name: Jane Doe"); with no such
    label, no PERSON/LOCATION pass runs at all. That's a deliberate trade-off: it
    means a name written in a bank's header without one of these labels could slip
    through, but the alternative — running NER over merchant-heavy transaction text —
    was reliably mangling real, non-PII descriptions instead.
    """
    if not text:
        return text

    analyzer = get_analyzer()
    anonymizer = get_anonymizer()

    whole_doc_results = analyzer.analyze(text=text, entities=ALWAYS_REDACTED_ENTITIES, language=language)
    sanitized = anonymizer.anonymize(text=text, analyzer_results=whole_doc_results).text

    # Process labels right-to-left so splicing a replacement of a different length at a
    # later position never shifts the still-to-be-processed earlier offsets.
    label_matches = list(ACCOUNT_HOLDER_LABEL_PATTERN.finditer(sanitized))
    for match in reversed(label_matches):
        window_start = match.end()
        window_end = min(len(sanitized), window_start + LABEL_WINDOW_CHARS)
        window = sanitized[window_start:window_end]

        window_results = analyzer.analyze(text=window, entities=["PERSON", "LOCATION"], language=language)
        window_sanitized = anonymizer.anonymize(text=window, analyzer_results=window_results).text

        sanitized = sanitized[:window_start] + window_sanitized + sanitized[window_end:]

    return sanitized
