import os
import logging
from cryptography.fernet import Fernet
from typing import Optional

logger = logging.getLogger(__name__)

_fernet: Optional[Fernet] = None

def get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = os.getenv("FERNET_KEY")
        if not key:
            logger.warning("FERNET_KEY not found in environment. Generating an ephemeral key. Data will not be decryptable after restart!")
            key = Fernet.generate_key()
            os.environ["FERNET_KEY"] = key.decode("utf-8")
        else:
            if isinstance(key, str):
                key = key.encode("utf-8")
        _fernet = Fernet(key)
    return _fernet

def encrypt_text(text: str) -> str:
    if not text:
        return text
    f = get_fernet()
    return f.encrypt(text.encode("utf-8")).decode("utf-8")

def decrypt_text(ciphertext: str) -> str:
    if not ciphertext:
        return ciphertext
    f = get_fernet()
    try:
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return ciphertext  # Return raw if decryption fails

_analyzer = None
_anonymizer = None

def get_presidio():
    global _analyzer, _anonymizer
    if _analyzer is None:
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_anonymizer import AnonymizerEngine
            
            # This requires spacy and the en_core_web_sm model to be installed.
            _analyzer = AnalyzerEngine()
            _anonymizer = AnonymizerEngine()
            logger.info("Presidio engines initialized.")
        except ImportError:
            logger.error("Presidio packages not installed. De-identification will be skipped.")
            return None, None
        except Exception as e:
            logger.error(f"Error initializing Presidio: {e}")
            return None, None
    return _analyzer, _anonymizer

def deidentify_text(text: str) -> str:
    """Scrub PII from the provided text using Presidio."""
    if not text:
        return text
    analyzer, anonymizer = get_presidio()
    if not analyzer or not anonymizer:
        return text
        
    try:
        # Analyze the text for common PII
        entities = ["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "US_SSN", "DATE_TIME", "LOCATION"]
        results = analyzer.analyze(text=text, entities=entities, language="en")
        
        # Anonymize (replaces with e.g. <PERSON>)
        anonymized_result = anonymizer.anonymize(text=text, analyzer_results=results)
        return anonymized_result.text
    except Exception as e:
        logger.error(f"De-identification failed: {e}")
        return text
