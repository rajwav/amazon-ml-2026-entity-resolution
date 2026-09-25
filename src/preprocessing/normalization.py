"""
Comprehensive Preprocessing and Normalization Module for Business Entity Resolution.
Supports multilingual records (US, India, France) including native Indic script transliteration.
Operates completely offline with zero external network or API dependencies.
"""

import re
import unicodedata
from typing import Dict, List, Set, Tuple, Optional

# --- Indic Script Transliteration Mapping ---
INDIC_OFFSET_MAP = {
    0x02: 'n', 0x03: 'h', 0x05: 'a', 0x06: 'a', 0x07: 'i', 0x08: 'i', 0x09: 'u', 0x0A: 'u',
    0x0B: 'ri', 0x0E: 'e', 0x0F: 'e', 0x10: 'ai', 0x12: 'o', 0x13: 'o', 0x14: 'au',
    0x15: 'k', 0x16: 'kh', 0x17: 'g', 0x18: 'gh', 0x19: 'ng',
    0x1A: 'ch', 0x1B: 'chh', 0x1C: 'j', 0x1D: 'jh', 0x1E: 'ny',
    0x1F: 't', 0x20: 'th', 0x21: 'd', 0x22: 'dh', 0x23: 'n',
    0x24: 't', 0x25: 'th', 0x26: 'd', 0x27: 'dh', 0x28: 'n', 0x29: 'nn',
    0x2A: 'p', 0x2B: 'ph', 0x2C: 'b', 0x2D: 'bh', 0x2E: 'm',
    0x2F: 'y', 0x30: 'r', 0x31: 'rr', 0x32: 'l', 0x33: 'll', 0x34: 'lll', 0x35: 'v',
    0x36: 'sh', 0x37: 'sh', 0x38: 's', 0x39: 'h',
    0x3E: 'a', 0x3F: 'i', 0x40: 'i', 0x41: 'u', 0x42: 'u', 0x43: 'ri',
    0x46: 'e', 0x47: 'e', 0x48: 'ai', 0x4A: 'o', 0x4B: 'o', 0x4C: 'au',
    0x4D: '', # virama / halant
}

def transliterate_indic(text: str) -> str:
    """Transliterate Indic scripts (Devanagari, Tamil, Telugu, Kannada, etc.) to Latin."""
    if not text:
        return ""
    res = []
    for c in text:
        cp = ord(c)
        if 0x0900 <= cp <= 0x0D7F:
            base = cp & 0xFF80
            off = cp - base
            if off in INDIC_OFFSET_MAP:
                res.append(INDIC_OFFSET_MAP[off])
            else:
                res.append(' ')
        else:
            res.append(c)
    out = ''.join(res)
    # collapse consecutive repeated vowels produced by matras (e.g. 'aa' -> 'a', 'ee' -> 'i')
    out = re.sub(r'a+', 'a', out)
    out = re.sub(r'e+', 'e', out)
    out = re.sub(r'i+', 'i', out)
    out = re.sub(r'o+', 'o', out)
    out = re.sub(r'u+', 'u', out)
    return out

# --- Legal Suffixes across US, India, and France ---
LEGAL_SUFFIX_PATTERNS = [
    # India
    (r'\b(pvt|private)\s+(ltd|limited)\b', 'pvt_ltd'),
    (r'\bprivate\s+limited\b', 'pvt_ltd'),
    (r'\bpublic\s+limited\b', 'pub_ltd'),
    (r'\b(llp|limited\s+liability\s+partnership)\b', 'llp'),
    (r'\b(ltd|limited)\b', 'ltd'),
    # US
    (r'\b(llc|l\.l\.c\.|limited\s+liability\s+co(mpany)?)\b', 'llc'),
    (r'\b(inc|incorporated|inc\.)\b', 'inc'),
    (r'\b(corp|corporation)\b', 'corp'),
    (r'\b(co|company)\b', 'co'),
    # France
    (r'\b(sarl|s\.a\.r\.l\.|societe\s+a\s+responsabilite\s+limitee)\b', 'sarl'),
    (r'\b(sas|s\.a\.s\.|societe\s+par\s+actions\s+simplifiee)\b', 'sas'),
    (r'\b(sci|s\.c\.i\.|societe\s+civile\s+immobiliere)\b', 'sci'),
    (r'\b(eurl|e\.u\.r\.l\.)\b', 'eurl'),
    (r'\b(sa|s\.a\.)\b', 'sa'),
]

LEGAL_STOPWORDS = {
    'inc', 'incorporated', 'corp', 'corporation', 'llc', 'ltd', 'limited', 'pvt',
    'private', 'co', 'company', 'services', 'enterprises', 'solutions', 'and', 'the',
    'of', 'in', 'group', 'holdings', 'technologies', 'industries', 'associates',
    'sarl', 'sas', 'sci', 'eurl', 'sa', 'llp', 'center', 'centre'
}

# --- Common Street / Address Abbreviations ---
ADDRESS_REPLACEMENTS = [
    (r'\bstreet\b', 'st'),
    (r'\broad\b', 'rd'),
    (r'\bavenue\b', 'ave'),
    (r'\bboulevard\b', 'blvd'),
    (r'\bboul\b', 'blvd'),
    (r'\br\.\b', 'blvd'),
    (r'\brue\b', 'rue'),
    (r'\bdrive\b', 'dr'),
    (r'\blane\b', 'ln'),
    (r'\bcourt\b', 'ct'),
    (r'\bplace\b', 'pl'),
    (r'\bterrace\b', 'ter'),
    (r'\bcircle\b', 'cir'),
    (r'\bhighway\b', 'hwy'),
    (r'\bexpressway\b', 'expy'),
    (r'\bparkway\b', 'pkwy'),
    (r'\bpost\s+office\s+box\b', 'pobox'),
    (r'\bp\s*o\s*box\b', 'pobox'),
    (r'\bapartment\b', 'apt'),
    (r'\bunit\b', 'unit'),
    (r'\bfloor\b', 'fl'),
    (r'\bnull\b', ' '),
    (r'\bnone\b', ' '),
    (r'\bna\b', ' '),
]

def strip_accents(text: str) -> str:
    """Normalize Unicode characters to decomposed form and remove diacritical marks."""
    if not text:
        return ""
    normalized = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in normalized if not unicodedata.combining(c))

def normalize_text_basic(text: str, enable_transliteration: bool = True) -> str:
    """Perform lowercase, optional Indic transliteration, accent stripping, and space normalization."""
    if not text:
        return ""
    # Transliterate Indic scripts if enabled
    if enable_transliteration:
        text = transliterate_indic(text)
    # Lowercase
    text = text.lower()
    # Strip accents / diacritics
    text = strip_accents(text)
    # Replace ampersands with 'and'
    text = text.replace('&', ' and ')
    # Replace slashes and hyphens with spaces for token separation
    text = re.sub(r'[\/\\_\-]+', ' ', text)
    # Remove leading/trailing formatting artifacts like <<, --, ##, ++, ()
    text = re.sub(r'[<>\#\*\+\(\)\[\]\"\'\:\;\,]', ' ', text)
    # Collapse multiple whitespaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def normalize_business_name(name: str, enable_transliteration: bool = True) -> Tuple[str, Optional[str], List[str], List[str]]:
    """
    Normalize a business name.
    Returns:
      - core_name: clean name with legal suffix stripped
      - legal_type: standardized legal suffix string (or None)
      - tokens: list of significant tokens (length >= 3, non-stopwords)
      - ngrams: list of character 3-grams
    """
    clean = normalize_text_basic(name, enable_transliteration=enable_transliteration)
    if not clean:
        return "", None, [], []
    
    # Identify and extract legal suffix
    detected_legal = None
    for pattern, legal_type in LEGAL_SUFFIX_PATTERNS:
        match = re.search(pattern, clean)
        if match:
            detected_legal = legal_type
            # remove the legal pattern from clean
            clean = re.sub(pattern, ' ', clean)
            break
            
    # Re-normalize whitespace after removal
    core_name = re.sub(r'\s+', ' ', clean).strip()
    if not core_name:
        core_name = normalize_text_basic(name, enable_transliteration=enable_transliteration) # fallback if entire name was legal suffix
        
    # Extract significant word tokens (length >= 3, non-stopword, alphabetical or alphanumeric)
    words = re.findall(r'\b[a-z0-9]{3,}\b', core_name)
    sig_tokens = [w for w in words if w not in LEGAL_STOPWORDS]
    if not sig_tokens and words:
        sig_tokens = words # keep whatever tokens exist if all were stopwords
        
    # Character 3-grams of the core name (ignoring spaces)
    compact = re.sub(r'\s+', '', core_name)
    ngrams = [compact[i:i+3] for i in range(len(compact)-2)] if len(compact) >= 3 else [compact]
    
    return core_name, detected_legal, sig_tokens, ngrams

def normalize_business_address(address: str, enable_transliteration: bool = True) -> Tuple[str, List[str], List[str]]:
    """
    Normalize a business address.
    Returns:
      - norm_address: normalized address string
      - digit_tokens: list of digit sequences (house numbers, PINs, zip codes)
      - location_tokens: list of non-number geographic/street tokens (len >= 3)
    """
    clean = normalize_text_basic(address, enable_transliteration=enable_transliteration)
    if not clean:
        return "", [], []
        
    # Apply standard street/address abbreviations
    for pattern, replacement in ADDRESS_REPLACEMENTS:
        clean = re.sub(pattern, replacement, clean)
        
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    # Extract all digit sequences (house numbers, ward numbers, postal codes)
    digits = re.findall(r'\b\d+\b', clean)
    
    # Extract location word tokens (length >= 3, non-digit)
    words = re.findall(r'\b[a-z]{3,}\b', clean)
    location_tokens = [w for w in words if w not in {'st', 'rd', 'ave', 'blvd', 'dr', 'ln', 'ct', 'pl', 'ter', 'hwy', 'apt', 'unit', 'fl', 'near', 'opp', 'road', 'street', 'avenue'}]
    
    return clean, digits, location_tokens
