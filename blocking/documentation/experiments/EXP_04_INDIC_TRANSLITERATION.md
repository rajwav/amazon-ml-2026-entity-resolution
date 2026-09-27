# Experiment 04: Indic Script Transliteration Ablation

| Attribute | Specification |
|:---|:---|
| **Experiment ID** | `EXP_04` |
| **Date Executed** | 2026-09-25 |
| **Author / Operator** | Entity Resolution Engineering Team |
| **Status** | **Completed & Verified (Adopted Selective Architecture)** |
| **Source Script** | [`experiments/blocking/transliteration.py`](../../../experiments/blocking/transliteration.py) |
| **Metrics Artifact** | [`experiments/results/exp4_transliteration_metrics.json`](../../../experiments/results/exp4_transliteration_metrics.json) |
| **Recovered Pairs Artifact** | [`experiments/results/exp4_transliteration_recovered_pairs.tsv`](../../../experiments/results/exp4_transliteration_recovered_pairs.tsv) |

---

## 1. Objective
Isolate and measure the exact impact of Indic script transliteration (`indic-transliteration` library covering Devanagari, Bengali, Gujarati, Kannada, Tamil, Telugu, Malayalam, Gurmukhi, Oriya to Latin ISO/ITRANS) across both the Core Backbone ($B+C+D+E$) and the full Baseline ($B+C+D+E+F$).

---

## 2. Hypothesis
Converting native Indic script strings to normalized Latin equivalents will bridge the lexical disconnect for Indian entities, recovering lost matches in name channels with minimal candidate overhead, while transliterating broad location fields may induce unneeded candidate bloat.

---

## 3. Starting Point / Baseline Reference
- Baseline G (`EXP_00`): Full 5-channel union with transliteration active (99.9449% recall, 3,294.6 avg cands).
- $B+C+D+E$ Backbone (`EXP_03`): 98.0859% recall, 836.1 avg cands.

---

## 4. Dataset & Benchmark Setup
- Standard 10k Pilot Benchmark:
  - 10,000 $S1$ queries (6,000 US, 4,000 India).
  - 84,481 target records.
  - 34,481 ground truth pairs.
  - Strict intra-country partitioning.

---

## 5. Method & Implementation Details
A rigorous $2 \times 2$ factorial ablation was executed on identical data:
1. **Config 1**: $B+C+D+E$ with Transliteration **OFF**
2. **Config 2**: $B+C+D+E$ with Transliteration **ON**
3. **Config 3**: $B+C+D+E+F$ with Transliteration **OFF**
4. **Config 4**: $B+C+D+E+F$ with Transliteration **ON** (Baseline G control)

Attribution analysis parsed every recovered pair to classify whether recovery originated from:
- Name transliteration
- Address digit / string transliteration
- Both

---

## 6. Code & Artifact References
- **Script**: [`experiments/blocking/transliteration.py`](../../../experiments/blocking/transliteration.py)
- **Metrics JSON**: [`experiments/results/exp4_transliteration_metrics.json`](../../../experiments/results/exp4_transliteration_metrics.json)
- **Recovered Pairs TSV**: [`experiments/results/exp4_transliteration_recovered_pairs.tsv`](../../../experiments/results/exp4_transliteration_recovered_pairs.tsv)

---

## 7. Results & Metrics Table

| Configuration | Transliteration | Recall % | Recalled | Missed | $\Delta$ Recalled | Avg Cands / $S1$ | $\Delta$ Cands / $S1$ | Median | P95 | Runtime |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **1. $B+C+D+E$** | **OFF** | 97.6625% | 33,675 | 806 | - | 831.2 | - | 370 | 3,556 | 1.54s |
| **2. $B+C+D+E$** | **ON** | **98.0859%** | **33,821** | **660** | **+146** | **836.1** | **+4.9** | **377** | **3,559** | 1.54s |
| **3. $B+C+D+E+F$**| **OFF** | **99.9565%** | **34,466** | **15** | - | **2,861.6** | - | 1,495 | 9,067 | 6.44s |
| **4. $B+C+D+E+F$**| **ON** | 99.9449% | 34,462 | 19 | -4 | 3,294.6 | +433.0 | 2,621 | 9,555 | 9.06s |

---

## 8. Candidate Volume & Distribution Analysis
- **In $B+C+D+E$ Backbone**: Enabling transliteration increased average candidates by only **+4.94 candidates per query** (from 831.2 to 836.1), representing an incremental cost of only **338 candidates per recovered true pair**.
- **In Full Baseline ($B+C+D+E+F$)**: Enabling transliteration on Channel F inflated candidates by **+433.0 candidates per query** (a massive jump of **+4,330,186 candidates**) without improving recall.

---

## 9. Recall & Recovery Analysis
- In the backbone, transliteration recovered **146 previously lost Indian business matches** (+0.4234% recall boost).
- Inspection of the 146 recovered pairs in [`exp4_transliteration_recovered_pairs.tsv`](../../../experiments/results/exp4_transliteration_recovered_pairs.tsv) demonstrated that **100% of the recoveries were driven by Name Transliteration** (Channels B, C, and D), such as:
  - `"Al Estate Private Limited"` $\leftrightarrow$ `"अल एस्टेट प्राइवेट लिमिटेड"`
  - `"Shyam International"` $\leftrightarrow$ `"ಶ್ಯಾಮ್ ಇಂಟರ್‌ನ್ಯಾಷನಲ್"`
  - `"Krishna Solutions Private Limited"` $\leftrightarrow$ `"ક્રિષ્ના Solutions પ્રાઇવેટ લિમિટેડ"`
- When broad location tokens (Channel F) were transliterated, common geographic syllables produced spurious phonetic cross-links that expanded candidate pools without recovering ground truth.

---

## 10. Failure / Error Analysis
- Enabling transliteration globally across Channel F caused 4 true pairs to be lost in the full baseline (dropping from 15 misses to 19 misses) due to index collision effects and noise saturation.
- Transliteration alone did not solve the short-name acronyms ("OM", "JB") or records with corrupted Romanized spellings.

---

## 11. Key Lessons Learned
1. **Transliteration is Essential for Indic Entity Names**: 146 Indian true pairs cannot be resolved without script conversion.
2. **Extreme Asymmetry**: Transliterating name channels is virtually free (+4.9 cands/S1), but transliterating location tokens creates a catastrophic candidate explosion (+433 cands/S1).
3. **The "Selective Transliteration" Principle**: Transliteration must be **ON for Name Channels (B, C, D)** and **OFF for Broad Location Channels (F)**.

---

## 12. Architectural Decision
- **Role**: **Selective Feature Transformation Pipeline**.
- **Decision**: Formally adopt **Selective Transliteration**:
  - Name Fields: Transliteration **ENABLED**.
  - Address Digits: Transliteration **ENABLED** (converting Indic numerals `०-९` to `0-9`).
  - Broad Location Fields: Transliteration **DISABLED**.

---

## 13. Impact on Subsequent Architecture
- Established the canonical preprocessing pipeline across all remaining experiments.
- Enabled the $B+C+D+E$ backbone to reach 98.0859% recall cleanly before applying tail recovery.
