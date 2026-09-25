"""
Comprehensive Preprocessing and Normalization Module for Business Entity Resolution.
Supports multilingual records (US, India, France) including native Indic script transliteration.
Operates completely offline with zero external network or API dependencies.
"""

import re
import unicodedata
from typing import Dict, List, Set, Tuple, Optional
from blocking.transliteration import transliterate_indic

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

US_STATES = {
    'al', 'ak', 'az', 'ar', 'ca', 'co', 'ct', 'de', 'fl', 'ga',
    'hi', 'id', 'il', 'in', 'ia', 'ks', 'ky', 'la', 'me', 'md',
    'ma', 'mi', 'mn', 'ms', 'mo', 'mt', 'ne', 'nv', 'nh', 'nj',
    'nm', 'ny', 'nc', 'nd', 'oh', 'ok', 'or', 'pa', 'ri', 'sc',
    'sd', 'tn', 'tx', 'ut', 'vt', 'va', 'wa', 'wv', 'wi', 'wy'
}

STOPWORDS_2CHAR = {'to', 'in', 'on', 'at', 'of', 'by', 'is', 'as', 'or', 'an', 'co', 'st', 'rd', 'no'}

def strip_accents(text: str) -> str:
    """Normalize Unicode characters to decomposed form (NFKD) and remove diacritical marks."""
    if not text:
        return ""
    normalized = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in normalized if not unicodedata.combining(c))

def normalize_text_basic(text: str, enable_transliteration: bool = True) -> str:
    """Perform lowercase, optional Indic transliteration, accent stripping, and space normalization."""
    if not text:
        return ""
    if enable_transliteration:
        text = transliterate_indic(text)
    text = text.lower()
    text = strip_accents(text)
    text = text.replace('&', ' and ')
    text = re.sub(r'[\/\\_\-]+', ' ', text)
    text = re.sub(r'[<>\#\*\+\(\)\[\]\"\'\:\;\,]', ' ', text)
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
    
    detected_legal = None
    for pattern, legal_type in LEGAL_SUFFIX_PATTERNS:
        match = re.search(pattern, clean)
        if match:
            detected_legal = legal_type
            clean = re.sub(pattern, ' ', clean)
            break
            
    core_name = re.sub(r'\s+', ' ', clean).strip()
    if not core_name:
        core_name = normalize_text_basic(name, enable_transliteration=enable_transliteration)
        
    words = re.findall(r'\b[a-z0-9]{3,}\b', core_name)
    sig_tokens = [w for w in words if w not in LEGAL_STOPWORDS]
    if not sig_tokens and words:
        sig_tokens = words
        
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
        
    for pattern, replacement in ADDRESS_REPLACEMENTS:
        clean = re.sub(pattern, replacement, clean)
        
    clean = re.sub(r'\s+', ' ', clean).strip()
    digits = re.findall(r'\b\d+\b', clean)
    words = re.findall(r'\b[a-z]{3,}\b', clean)
    location_tokens = [w for w in words if w not in {'st', 'rd', 'ave', 'blvd', 'dr', 'ln', 'ct', 'pl', 'ter', 'hwy', 'apt', 'unit', 'fl', 'near', 'opp', 'road', 'street', 'avenue'}]
    
    return clean, digits, location_tokens

def clean_domain_or_handle(name: str) -> str:
    """Extract domain stem or social handle stem, stripping protocols and extensions."""
    if not name:
        return ""
    n = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('utf-8').lower()
    n = re.sub(r'https?://|www\.|\.(com|org|net|in|co|io|biz|info|us|fr).*|[@#]', '', n)
    n = re.sub(r'[^a-z0-9]', '', n)
    return n

def collapse_double_consonants(name: str) -> str:
    """Collapse consecutive duplicate consonants (e.g. 'll' -> 'l', 'tt' -> 't')."""
    return re.sub(r'([b-df-hj-np-tv-z])\1+', r'\1', name.lower())

def extract_clean_digits(addr: str) -> List[str]:
    """Extract all digit sequences with ordinal suffix stripping and leading-zero normalization."""
    if not addr:
        return []
    addr_clean = re.sub(r'(\d+)(st|nd|rd|th)\b', r'\1', addr.lower())
    digits_raw = re.findall(r'\d+', addr_clean)
    digits = []
    for d in digits_raw:
        try:
            d_norm = str(int(d))
            if d_norm not in digits:
                digits.append(d_norm)
        except ValueError:
            continue
    return digits

def extract_2char_tokens(name: str) -> List[str]:
    """Extract standalone 2-letter uppercase or abbreviation tokens excluding common prepositions."""
    if not name:
        return []
    words = re.findall(r'\b[a-zA-Z]{2}\b', name)
    valid = []
    for w in words:
        wl = w.lower()
        if wl not in STOPWORDS_2CHAR and wl not in valid:
            valid.append(wl)
    return valid

def extract_consonant_trigram(name: str) -> str:
    """Extract first 3 consonants of business name core (ignoring vowels and non-letters)."""
    core_clean = re.sub(r'[^a-zA-Z]', '', name.lower())
    cons = re.sub(r'[aeiou]', '', core_clean)
    return cons[:3] if len(cons) >= 3 else ""

def extract_alphanumeric_units(addr: str) -> List[str]:
    """Extract alphanumeric unit tokens like 3a, 3b, 104b, f1118."""
    if not addr:
        return []
    units = re.findall(r'\b\d+[a-zA-Z]\b|\b[a-zA-Z]\d+\b', addr.lower())
    return [u for u in units if len(u) <= 5]

def extract_state_code(addr: str, country: str) -> str:
    """Extract US state code if country is US."""
    if country != 'US' or not addr:
        return ""
    words = re.findall(r'\b[a-zA-Z]{2}\b', addr.lower())
    for w in reversed(words):
        if w in US_STATES:
            return w
    return ""

def extract_short_street_tokens(addr: str) -> List[str]:
    """Extract 2-character street name tokens."""
    if not addr:
        return []
    words = re.findall(r'\b[a-zA-Z]{2}\b', addr.lower())
    valid = [w for w in words if w not in STOPWORDS_2CHAR and w not in US_STATES and w not in {'st', 'rd', 'ln', 'ct', 'dr', 'pl'}]
    return valid
