"""
Curated Reference Entity Fixtures for the Interactive Explorer.
Derived from real-world entity resolution patterns and project benchmark scenarios.
Contains zero personal names, private paths, or internal IDs.
"""

DEMO_CASES = {
    "CASE-01": {
        "id": "CASE-01",
        "title": "Apex Healthcare Solutions Pvt Ltd",
        "category": "Corporate Legal Suffix Variations",
        "sector": "Healthcare & Life Sciences",
        "s1_name": "Apex Healthcare Solutions Pvt Ltd",
        "s1_addr": "Plot 45, Sector 18, Electronic City, Bangalore",
        "country": "India",
        "description": "Standard corporate abbreviation expansion ('Pvt Ltd' vs 'Private Limited') and industrial address normalization.",
        "candidates": [
            {
                "source": "Source 2",
                "name": "Apex Healthcare Solutions Private Limited",
                "address": "45, Sector 18, Electronic City Phase 1, Bangalore, Karnataka",
                "country": "India",
                "expected_match": True,
                "notes": "Expanded legal suffix and locality phase suffix"
            },
            {
                "source": "Source 2",
                "name": "Apex Healthcare Solutions Pvt. Ltd.",
                "address": "Plot No 45, Sector-18, Electronic City, Bangalore",
                "country": "India",
                "expected_match": True,
                "notes": "Punctuation in legal suffix and hyphenated sector number"
            },
            {
                "source": "Source 3",
                "name": "Apex Healthcare Solutions",
                "address": "45 Electronic City, Bengaluru, KA",
                "country": "India",
                "expected_match": True,
                "notes": "Truncated legal suffix and state code abbreviation (KA)"
            },
            {
                "source": "Source 3",
                "name": "Apex Diagnostics & Clinic",
                "address": "102 Richmond Circle, Bangalore",
                "country": "India",
                "expected_match": False,
                "notes": "Shared prefix token 'Apex' but different business sector and address"
            }
        ]
    },
    "CASE-02": {
        "id": "CASE-02",
        "title": "Kim & Cervantes LLC",
        "category": "Address Range & Street Abbreviations",
        "sector": "Professional & Legal Services",
        "s1_name": "Kim & Cervantes LLC",
        "s1_addr": "27913 Bass Boulevard, Harlingen, TX",
        "country": "US",
        "description": "Exhibits digit prefix corruption ('97913' vs '27913') and address range notation ('27913-27917 Bass Blvd').",
        "candidates": [
            {
                "source": "Source 2",
                "name": "KIM & CERVANTES LLC",
                "address": "97913 BASS BOULEVARD, HARLINGEN, TX",
                "country": "US",
                "expected_match": True,
                "notes": "Uppercase normalization with a single-digit street number typo"
            },
            {
                "source": "Source 3",
                "name": "Kim & Cervantes",
                "address": "27913-27917 Bass Blvd, Harlingen, Texas",
                "country": "US",
                "expected_match": True,
                "notes": "Address range with street abbreviation ('Blvd') and spelled-out state"
            },
            {
                "source": "Source 2",
                "name": "Kim Family Dentistry PLLC",
                "address": "1400 Bass Blvd, Harlingen, TX",
                "country": "US",
                "expected_match": False,
                "notes": "Shares surname 'Kim' and street name, but distinct healthcare entity"
            }
        ]
    },
    "CASE-03": {
        "id": "CASE-03",
        "title": "Swastik Infra Private Limited",
        "category": "Multilingual & Script Variation",
        "sector": "Infrastructure & Construction",
        "s1_name": "Swastik Infra Private Limited",
        "s1_addr": "A-503, Vertex Vikas Bldg, Sir M V Road, Andheri East, Mumbai",
        "country": "India",
        "description": "Entity cataloged under bilingual representations (English and Devanagari script) with commercial complex address details.",
        "candidates": [
            {
                "source": "Source 2",
                "name": "Swastik Private Infra Limited",
                "address": "DOOR NO C-29 A-503, VERTEX VIKAS BLDG, SIR M V ROAD, MUMBAI, महाराष्ट्र",
                "country": "India",
                "expected_match": True,
                "notes": "Word transposition ('Private Infra') and door prefix in address"
            },
            {
                "source": "Source 3",
                "name": "Swastik Infra [स्वस्तिक इंफ्रा]",
                "address": "A-503, Greater Mumbai, Mumbai, MH",
                "country": "India",
                "expected_match": True,
                "notes": "Bilingual Devanagari notation in brackets with municipal jurisdiction"
            },
            {
                "source": "Source 2",
                "name": "Swastik Enterprises",
                "address": "Plot 10, MIDC, Nagpur, Maharashtra",
                "country": "India",
                "expected_match": False,
                "notes": "Generic token 'Swastik' located in an entirely different city (Nagpur)"
            }
        ]
    },
    "CASE-04": {
        "id": "CASE-04",
        "title": "Jacobs, Walter & Mcelroy LLC",
        "category": "Word Transposition & Typo Noise",
        "sector": "Consulting & Corporate Services",
        "s1_name": "Jacobs, Walter & Mcelroy LLC",
        "s1_addr": "14590 4, Hartford, AL",
        "country": "US",
        "description": "Severe lexical reordering in cataloging ('JACOBS, WALTER LLC MCELROY (&)') and optical character recognition errors ('Mcelrmy').",
        "candidates": [
            {
                "source": "Source 2",
                "name": "JACOBS, WALTER LLC MCELROY (&)",
                "address": "4, HARTFORD, AL",
                "country": "US",
                "expected_match": True,
                "notes": "Inverted name order, embedded ampersand notation, and concise address"
            },
            {
                "source": "Source 3",
                "name": "Jacobs, Walter & Mcelrmy LLC",
                "address": "14590b 4, Hartford, Alabama",
                "country": "US",
                "expected_match": True,
                "notes": "OCR character substitution ('rn' -> 'm' in Mcelrmy) and subunit '14590b'"
            },
            {
                "source": "Source 3",
                "name": "Jacobs Engineering Group",
                "address": "100 Main St, Birmingham, AL",
                "country": "US",
                "expected_match": False,
                "notes": "Unrelated corporation sharing initial surname token in same state"
            }
        ]
    },
    "CASE-05": {
        "id": "CASE-05",
        "title": "Garg Decor Pvt. Ltd.",
        "category": "Multi-Source Cluster & Domain Alias",
        "sector": "Retail & Home Furnishings",
        "s1_name": "Garg Decor Pvt. Ltd.",
        "s1_addr": "B-42, Tarang Apartments, Plot No. 19, I.P Extn., East Delhi, Delhi",
        "country": "India",
        "description": "Multi-source clustering scenario: matches appear as uppercase records, web domain aliases ('gargdecor.com'), and service abbreviations.",
        "candidates": [
            {
                "source": "Source 2",
                "name": "GARG DECOR PVT. LTD.",
                "address": "B-42, TARANG APARTMENTS, PLOT NO. 19, I.P EXTN., EAST DEHI, Delhi",
                "country": "India",
                "expected_match": True,
                "notes": "Uppercase capitalization with minor typo in district ('EAST DEHI')"
            },
            {
                "source": "Source 2",
                "name": "gargdecor.com",
                "address": "B-42, TARANG APARTMENTS, PLOT NO. 19, I.P EXTN., EAST DELHI, Delhi",
                "country": "India",
                "expected_match": True,
                "notes": "Entity identified by its digital web domain representation"
            },
            {
                "source": "Source 3",
                "name": "Garg Pvt. Ltd. [Services]",
                "address": "B-42, East Delhi, null, DL",
                "country": "India",
                "expected_match": True,
                "notes": "Truncated business descriptor with state code abbreviation (DL)"
            },
            {
                "source": "Source 2",
                "name": "Garg Decorators & Event Services",
                "address": "Plot 12, Sector 15, Rohini, Delhi",
                "country": "India",
                "expected_match": False,
                "notes": "Hard negative: similar trade name located in Rohini rather than I.P. Extension"
            }
        ]
    },
    "CASE-06": {
        "id": "CASE-06",
        "title": "Federal Bank Commercial Branch",
        "category": "Conflicting Branch Unit Numbers",
        "sector": "Banking & Financial Institutions",
        "s1_name": "Federal Bank Branch 104",
        "s1_addr": "Building 5, Commercial Complex, Sector 22, Chandigarh",
        "country": "India",
        "description": "Challenging hard negative scenario: identical corporate branding operating distinct branch facilities with conflicting numeric unit IDs.",
        "candidates": [
            {
                "source": "Source 2",
                "name": "Federal Bank Ltd (Branch 104)",
                "address": "Commercial Complex, Sector 22-B, Chandigarh",
                "country": "India",
                "expected_match": True,
                "notes": "Matching branch digit '104' with subsector notation '22-B'"
            },
            {
                "source": "Source 3",
                "name": "Federal Bank Branch 208",
                "address": "Building 5, Commercial Complex, Sector 22, Chandigarh",
                "country": "India",
                "expected_match": False,
                "notes": "Hard negative: identical building location but conflicting branch number '208'"
            },
            {
                "source": "Source 2",
                "name": "Federal Bank ATM & E-Lobby",
                "address": "SCO 45, Sector 17, Chandigarh",
                "country": "India",
                "expected_match": False,
                "notes": "ATM facility in adjacent sector"
            }
        ]
    }
}
