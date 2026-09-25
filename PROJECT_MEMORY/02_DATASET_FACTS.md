# 02 DATASET FACTS: VERIFIED GROUND TRUTH

*Rule: If a number or property is not documented in this file or verified directly from the dataset, it cannot be presented as a fact.*

## 1. File Inventory & Specifications

| Split | File Name | Size (MB) | Exact Rows | Unique IDs | Missing Values | Country Breakdown |
| :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **Train** | `train_source1.tsv` | 200.34 MB | 2,206,821 | 2,206,821 | None (0) | US: 1,323,633 (60.0%)<br>India: 883,188 (40.0%) |
| **Train** | `train_source2.tsv` | 466.63 MB | 5,034,616 | 5,034,616 | `business_address`: 168,967 (3.36%) | US: 3,016,817 (59.9%)<br>India: 2,017,799 (40.1%) |
| **Train** | `train_source3.tsv` | 480.37 MB | 5,285,603 | 5,285,603 | `business_address`: 175,916 (3.33%) | US: 3,170,056 (60.0%)<br>India: 2,115,547 (40.0%) |
| **Train** | `train_ground_truth.tsv`| 121.13 MB | 2,206,821 | 2,206,821 | `matched_entity_ids`: 123,247 (5.58%) | N/A |
| **Test** | `test_source1.tsv` | 166.91 MB | 1,732,544 | 1,732,544 | None (0) | India: 809,986 (46.8%)<br>US: 663,106 (38.3%)<br>France: 259,452 (15.0%) |
| **Test** | `test_source2.tsv` | 485.86 MB | 4,887,273 | 4,887,273 | `business_address`: 129,408 (2.65%) | India: 2,312,565 (47.3%)<br>US: 1,871,330 (38.3%)<br>France: 703,378 (14.4%) |
| **Test** | `test_source3.tsv` | 482.56 MB | 5,082,316 | 5,082,316 | `business_address`: 136,098 (2.68%) | India: 2,405,000 (47.3%)<br>US: 1,945,701 (38.3%)<br>France: 731,615 (14.4%) |

## 2. Ground Truth Structural Facts
- **Total True Pairs in Train:** Exactly **7,638,365 pairs** (S2: 3,693,619 | S3: 3,944,746).
- **Match Cardinality Distribution per S1:**
  - 0 matches (Singletons): 123,247 (5.58%)
  - 1 match: 119,157 (5.40%)
  - 2 matches: 375,212 (17.00%)
  - 3 matches: 530,841 (24.05%)
  - 4 matches: 484,115 (21.94%)
  - 5 matches: 321,957 (14.59%)
  - 6 matches: 164,868 (7.47%)
  - 7 matches: 63,968 (2.90%)
  - $\ge 8$ matches: 23,456 (1.06%) [Max matches for single S1: 11]
- **Target Record Invariant:**
  - Every S2 record maps to **at most one** S1 entity (multiple matches: 0).
  - Every S3 record maps to **at most one** S1 entity (multiple matches: 0).
  - Distractor records (unmatched): S2 has 1,340,997 (26.64%); S3 has 1,340,857 (25.37%).
- **Country Isolation Invariant:**
  - Cross-country true matches: **EXACTLY 0** (out of 7,638,365 pairs). True matches are 100% intra-country.

## 3. Persistent 10,000-S1 Pilot Facts
- **Source 1 Sample:** Exactly 10,000 entities (`pilot_s1.tsv`, seed 42):
  - 6,000 US: 335 zero-match, 324 1-match, 5,341 multi-match.
  - 4,000 India: 223 zero-match, 216 1-match, 3,561 multi-match.
- **True Ground Truth Pairs:** Exactly **34,481 true pairs** across 34,481 unique target records (`pilot_ground_truth.tsv`).
- **Target Search Pool:** Exactly **84,481 records** (34,481 true matched records + 50,000 distractors: 25k S2, 25k S3) (`pilot_targets.tsv`).
- **Target Pool by Country:** US = 50,522; India = 33,959.

## 4. Known Noise Patterns
- **Legal Suffixes:** Suffix additions, removals, reorderings (`Inc`, `Incorporated`, `LLC`, `L.L.C.`, `Pvt Ltd`, `Private Limited`, `SARL`, `SAS`, `SCI`).
- **Punctuation & Formatting:** Leading symbols (`--`, `<<`, `##`, `+`), uppercase blocks, string `"null"` in addresses.
- **Typographical Errors:** Transpositions, insertions, phonetic spelling (`Enterprises` $\rightarrow$ `Enterpires`, `ENRTPRMISES`).
- **Multilingual / Cross-Script:** 7.46% of Indian names in S2/S3 use Indic scripts (Devanagari, Tamil, Telugu, Kannada) while S1 is Latin transliterated.
