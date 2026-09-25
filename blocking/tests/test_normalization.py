"""
Unit tests for text normalization, Indic transliteration, and tail feature extractors.
"""

import pytest
from blocking.transliteration import transliterate_indic
from blocking.normalization import (
    strip_accents,
    normalize_text_basic,
    normalize_business_name,
    normalize_business_address,
    clean_domain_or_handle,
    collapse_double_consonants,
    extract_clean_digits,
    extract_2char_tokens,
    extract_consonant_trigram,
    extract_alphanumeric_units,
    extract_state_code
)

def test_indic_transliteration():
    # Hindi Devanagari test
    devanagari = "अल एस्टेट प्राइवेट लिमिटेड"
    trans = transliterate_indic(devanagari)
    assert "al" in trans.lower()
    assert "estet" in trans.lower() or "estate" in trans.lower()

    # Kannada test
    kannada = "ಶ್ಯಾಮ್ ಇಂಟರ್‌ನ್ಯಾಷನಲ್"
    trans_k = transliterate_indic(kannada)
    assert len(trans_k) > 0

def test_accent_stripping():
    french = "Équipe École et Hôtel à Bordeaux"
    stripped = strip_accents(french)
    assert stripped == "Equipe Ecole et Hotel a Bordeaux"

def test_business_name_normalization():
    # US legal suffix
    core, legal, sig_tokens, _ = normalize_business_name("Zephay Labs Inc")
    assert core == "zephay labs"
    assert legal == "inc"
    assert "zephay" in sig_tokens

    # French legal suffix
    core_fr, legal_fr, sig_fr, _ = normalize_business_name("Marina Ecole France Sarl")
    assert legal_fr == "sarl"
    assert "marina" in sig_fr

def test_domain_and_handle_extraction():
    url = "https://www.empirecastillo.com/home"
    stem = clean_domain_or_handle(url)
    assert stem == "empirecastillo"

    handle = "@SIBYLSBAKERY"
    h_stem = clean_domain_or_handle(handle)
    assert h_stem == "sibylsbakery"

def test_double_consonant_collapse():
    assert collapse_double_consonants("castillo") == "castilo"
    assert collapse_double_consonants("wllrow") == "wlrow"
    assert collapse_double_consonants("mallone") == "malone"

def test_clean_digits_and_ordinals():
    addr = "10848 54th Lane, Suite 001711"
    digits = extract_clean_digits(addr)
    assert "10848" in digits
    assert "54" in digits
    assert "1711" in digits

def test_consonant_trigrams():
    assert extract_consonant_trigram("Willow") == "wll"
    assert extract_consonant_trigram("K Willow") == "kwl"

def test_alphanumeric_units():
    addr = "4th Floor, Unit 4B, Room 104A, Apt 3a"
    units = extract_alphanumeric_units(addr)
    assert "4b" in units
    assert "104a" in units
    assert "3a" in units

def test_state_code():
    assert extract_state_code("2621 Cotten Road, Tyler, TX", "US") == "tx"
    assert extract_state_code("Mumbai, Maharashtra", "India") == ""
