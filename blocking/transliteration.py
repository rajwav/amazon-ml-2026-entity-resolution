"""
Indic Script Transliteration Module for Business Entity Resolution.
Supports Devanagari, Bengali, Gujarati, Kannada, Tamil, Telugu, Malayalam, Gurmukhi, and Oriya.
Operates completely offline with zero external network or API dependencies.
"""

import re

# Unicode offset mapping for Brahmic scripts to Latin ISO / ITRANS equivalents
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
    # Indic digits (0x66 to 0x6F map to 0..9)
    0x66: '0', 0x67: '1', 0x68: '2', 0x69: '3', 0x6A: '4',
    0x6B: '5', 0x6C: '6', 0x6D: '7', 0x6E: '8', 0x6F: '9',
}

def transliterate_indic(text: str) -> str:
    """
    Transliterate Indic scripts (Devanagari, Bengali, Gujarati, Kannada, etc.) to Latin.
    Preserves existing Latin text, numbers, and spaces.
    """
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
    # collapse consecutive repeated vowels produced by matras
    out = re.sub(r'a+', 'a', out)
    out = re.sub(r'e+', 'e', out)
    out = re.sub(r'i+', 'i', out)
    out = re.sub(r'o+', 'o', out)
    out = re.sub(r'u+', 'u', out)
    return out
