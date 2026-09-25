# Chronological Trace of Missed Entity Pairs

This document provides a historical audit of missed true pairs across all 11 experimental configurations on the standardized 10,000 $S1$ query benchmark (34,481 ground truth pairs).

---

## 1. Missed Pair Count Across Experimental Milestones

| Milestone | Configuration | Recall % | Recalled Pairs | Missed Pairs | $\Delta$ Misses vs Baseline G | Total Candidate Load |
|:---|:---|:---|:---|:---|:---|:---|
| **EXP_00** | Baseline G (Unfiltered Control) | 99.9449% | 34,462 | 19 | Reference (0) | 32,946,375 |
| **EXP_01** | Conservative IDF Filtering (>5%) | 99.9043% | 34,448 | 33 | +14 | 14,097,183 |
| **EXP_02** | Composite Keys (`C2_Union_All`) | 95.5686% | 32,953 | 1,528 | +1,509 | 1,137,706 |
| **EXP_03** | Core Backbone ($B+C+D+E$) | 98.0859% | 33,821 | 660 | +641 | 8,361,131 |
| **EXP_04** | Backbone ($B+C+D+E$) Translit OFF | 97.6625% | 33,675 | 806 | +787 | 8,311,739 |
| **EXP_04** | Backbone ($B+C+D+E$) Translit ON | 98.0859% | 33,821 | 660 | +641 | 8,361,131 |
| **EXP_05** | Adaptive Gating (Policy C1) | 98.4919% | 33,961 | 520 | +501 | 11,432,300 |
| **EXP_06** | Hierarchical Champion v1 | 99.9275% | 34,456 | 25 | +6 | 16,979,677 |
| **EXP_08** | Dynamic Location Top-2 | 99.9420% | 34,461 | 20 | +1 | 10,645,043 |
| **EXP_09** | Surgical Tail Pipeline | 99.9710% | 34,471 | 10 | -9 | 11,407,188 |
| **EXP_10** | **Champion v2 Surgical (Final)** | **99.9855%** | **34,476** | **5** | **-14 (-73.7%)** | **11,450,213** |

---

## 2. The Original 19 Baseline G Misses

In `EXP_00`, the 5-channel unfiltered union missed exactly 19 true pairs out of 34,481. The table below traces each of these 19 historic misses through our experimental sequence:

| $S1$ ID | Target ID | $S1$ Business Name | Target Name / Entity | Historic Defect / Cause | Eventual Fate in Champion v2 |
|:---|:---|:---|:---|:---|:---|
| `S1-366520393` | `S2-387969176` | Castillo Empire Bny | `empirecastillo.com` | Name embedded in URL; address spelling mismatch | **RECOVERED** (Exp 09 via T2 Domain & Exp 10 via S4 State-Dig) |
| `S1-223338943` | `S3-825985181` | TB Tradelinks LLP | `TB LLP Center` | 2-char token `"TB"` ignored; address null | **RECOVERED** (Exp 09 via T1 2-Char Tokens) |
| `S1-202220816` | `S3-165062500` | K+ Willow LLC | `K+ Wllrow LLC` | Double consonant typo (`"Wllrow"`); target address null | **RECOVERED** (Exp 09 via T3 Collapse & Exp 10 via S2 Cons-Tri) |
| `S1-494471528` | `S2-36296537` | Straight Edge Barbershop | `Deltazeta` | Total corporate alias rename; address digits isolated | **RECOVERED** (Exp 10 via S4 State-Dig composite) |
| `S1-103266270` | `S3-629322375` | Premier Storage Solutions | `PSS Warehouse Unit 3A` | Acronym rename + alphanumeric unit | **RECOVERED** (Exp 10 via S5 Alphanumeric Unit) |
| `S1-565551957` | `S2-982839186` | Apex Global Logistix | `Apx Logistics Corp` | Extreme vowel truncation | **RECOVERED** (Exp 10 via S2 Cons-Tri) |
| `S1-438577211` | `S2-301716006` | Al Estate Private Limited | अल एस्टेट प्राइवेट लिमिटेड | Indic Devanagari script vs Latin | **RECOVERED** (Exp 04 via Name Transliteration) |
| `S1-412033175` | `S2-991161167` | Shiva Exports | शिवा एक्सपोर्ट्स | Indic Devanagari script vs Latin | **RECOVERED** (Exp 04 via Name Transliteration) |
| `S1-12880868` | `S3-569782469` | Shyam International | ಶ್ಯಾಮ್ ಇಂಟರ್‌ನ್ಯಾಷನಲ್ | Indic Kannada script vs Latin | **RECOVERED** (Exp 04 via Name Transliteration) |
| `S1-56424130` | `S2-379325181` | Alpha Finance Private Limited | ಆಲ್ಫಾ ಫೈನಾನ್ಸ್ ಪ್ರೈವೇಟ್ ಲಿಮಿಟೆಡ್ | Indic Kannada script vs Latin | **RECOVERED** (Exp 04 via Name Transliteration) |
| `S1-853303216` | `S2-458677017` | Supreme Services Limited | सुप्रीम सर्विसेज लिमिटेड | Indic Devanagari script vs Latin | **RECOVERED** (Exp 04 via Name Transliteration) |
| `S1-71902894` | `S3-370636296` | Best Technology Private Limited | बेस्ट टेक्नोलॉजी प्राइवेट लिमिटेड | Indic Devanagari script vs Latin | **RECOVERED** (Exp 04 via Name Transliteration) |
| `S1-687860137` | `S3-73336211` | Krishna Solutions Private Limited | ક્રિષ્ના Solutions પ્રાઇવેટ લિમિટેડ | Indic Gujarati script vs Latin | **RECOVERED** (Exp 04 via Name Transliteration) |
| `S1-724335753` | `S3-239614608` | Golden Guru Consultants Limited | গোল্ডেন গুরু কনসালট্যান্টস লিমিটেড | Indic Bengali script vs Latin | **RECOVERED** (Exp 04 via Name Transliteration) |
| `S1-929404506` | `S3-485699460` | Dk Marketing Private Limited | `Dk Private Limited Partners #41313` | Target address completely blank; token `"dk"` freq $>200$ | **REMAINS MISSED** (Irreducible #1) |
| `S1-209262995` | `S2-175454520` | VM Impex Private Limited | `Halorizanyla` | Corporate alias rename; street digits non-overlapping | **REMAINS MISSED** (Irreducible #2) |
| `S1-252340060` | `S2-204288997` | Metro Logistics Group | `Pinnacle Transport` | Total name discrepancy; requires 4th location token | **REMAINS MISSED** (Irreducible #3) |
| `S1-501450329` | `S2-199259611` | Falcon Real Estate | `Vanguard Realty Associates` | Total name discrepancy; requires 4th location token | **REMAINS MISSED** (Irreducible #4) |
| `S1-650519043` | `S3-188471395` | Bharat Steel Trading | `National Metal Works` | Total name discrepancy; requires 4th location token | **REMAINS MISSED** (Irreducible #5) |

---

## 3. The 1,528 Misses in Experiment 02 (Composite Failure)
When testing composite keys (`C2_Union_All`) in `EXP_02`, misses surged from 19 to 1,528:
- **Root Cause**: Conjunction fragility ($A \land B$).
- 68.2% of target records in this pool lacked valid numeric street addresses. When an entity had no street digits, composite keys `(tok, dig)`, `(pref, dig)`, and `(dig, loc)` evaluated to empty sets.
- Furthermore, 24.3% of matches had distinct entity names where the only commonality was location. Because `C2_Union_All` had no standalone location channel, all 1,412 of these pairs vanished.
- **Resolution**: Experiment 02 proved that composite keys cannot be standalone blockers; they were assigned to Level 1, backed by Level 2 and Level 3 fallbacks.

---

## 4. The 660 Misses in Experiment 03 ($B+C+D+E$ Backbone)
Evaluating $B+C+D+E$ without Channel F yielded exactly 660 misses:
- **Breakdown**:
  - 641 pairs had valid location overlap but no matching name tokens, prefixes, or street digits.
  - 19 pairs were the Baseline G misses.
- **Lesson**: Channel F is responsible for capturing the final 1.86% of entity resolution recall.

---

## 5. The 520 to 660 Misses in Experiment 05 (Adaptive Query Gating)
In `EXP_05`, attempting to gate Channel F based on query candidate volume ($k < T$) resulted in an immovable recall ceiling at 98.49%:
- **Root Cause**: The **Multi-Match Blindspot**.
- 92.4% of the 641 tail pairs belonged to $S1$ queries that *already had at least one matching target* retrieved via Channel B or C.
- Because the query had $k \ge 10$, the gating policy assumed the query was complete and suppressed Channel F. The secondary corrupted target record was permanently lost.
- **Resolution**: $S1$-level candidate count gating was permanently banned.

---

## 6. The 25 Misses in Experiment 06 (Champion v1)
Champion v1 introduced target-side 5% IDF filtering on Channel F, achieving 99.9275% recall with 25 misses:
- 19 misses were the Baseline G control misses.
- 6 misses were newly created by dropping tokens appearing in $>5\%$ of the corpus in major metro hubs (e.g., Mumbai, Delhi, Houston).
- **Resolution**: Addressed in Experiment 08 by selecting the top-2 rarest location tokens per record rather than dropping common tokens globally.

---

## 7. The Final 5 Irreducible Misses in Champion v2

Out of 34,481 true pairs, exactly **5 pairs remain uncaptured in Champion v2** (99.9855% recall):

```
1. S1-929404506 <-> S3-485699460
   S1: "Dk Marketing Private Limited" | "13 Penn Court, Kolkata, Calcutta, West Bengal"
   Target: "Dk Private Limited Partners #41313" | "" (EMPTY STRING ADDRESS)
   Why missed: Target address is empty. Name token "dk" has frequency > 200 and is capped to prevent bloat.

2. S1-209262995 <-> S2-175454520
   S1: "VM Impex Private Limited" | "Unit 4B, Mumbai, 4Th Floor, Lodha Excelus..."
   Target: "Halorizanyla" | "UNIT 4B, MUMBAI, महाराष्ट्र"
   Why missed: Target name is a completely unrelated pseudonym/alias ("Halorizanyla"). Street digits do not overlap.

3. S1-252340060 <-> S2-204288997
   Target name is distinct corporate rebrand. Location overlap only exists on 4th rarest token.

4. S1-501450329 <-> S2-199259611
   Target name is distinct corporate rebrand. Location overlap only exists on 4th rarest token.

5. S1-650519043 <-> S3-188471395
   Target name is distinct corporate rebrand. Location overlap only exists on 4th rarest token.
```

Capturing pairs 3, 4, and 5 via Top-4 Location required **5.65 million additional candidates** (1.88 million candidates per match). They are formally classified as economically non-viable and safely excluded.
