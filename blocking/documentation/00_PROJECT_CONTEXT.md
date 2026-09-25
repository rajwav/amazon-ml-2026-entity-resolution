# 00 Project Context: Problem Framing & Operating Envelope

> **Amazon ML Challenge 2026 — Business Entity Resolution**  
> **Role:** Lead ML Engineer & Documentation Architect  

---

## 1. Challenge Overview

Business Entity Resolution (ER) is the task of determining whether two or more distinct business entity records from disparate, heterogeneous sources refer to the exact same real-world corporate or commercial entity.

In modern e-commerce and supply chain networks, business records arrive from vendor portals, public company registries, licensing databases, web scraping, and shipping invoices. These sources present massive discrepancies:
- Severe optical character recognition (OCR) and typographical errors.
- Unstandardized legal entity designators (e.g. `LLC`, `L.L.C.`, `Limited Liability Company`, `Pvt Ltd`, `SARL`).
- Partial or missing addresses (3.3% of records lack address entirely).
- Out-of-order address components (e.g. city appearing before street name).
- Native non-Latin scripts (Devanagari, Tamil, Telugu, Kannada, Bengali) vs romanized/transliterated Latin representations.
- Web domains and social media handles masquerading as business names (e.g. `empirecastillo.com`, `@SIBYLSBAKERY`).

---

## 2. Competition Objectives & Metric

### 2.1 The Evaluation Metric: Macro $F_{0.5}$
Submissions are evaluated on **Macro $F_{0.5}$** across all test queries:
$$F_{0.5} = \frac{(1 + 0.5^2) \cdot \text{Precision} \cdot \text{Recall}}{0.5^2 \cdot \text{Precision} + \text{Recall}} = \frac{1.25 \cdot P \cdot R}{0.25 \cdot P + R}$$

Macro $F_{0.5}$ weights precision twice as heavily as recall:
- A false positive (incorrectly linking two unrelated businesses) penalizes the score $4\times$ more severely than a false negative.
- However, during the initial **Candidate Generation / Blocking** phase, **Recall is the hard prerequisite**. If a true matching business record is pruned during blocking, downstream classification precision on that pair is moot because the pair is absent from the candidate pool.

---

## 3. Strict Operating Envelope & Guardrails

The project operates under rigid technical rules established at the onset:
1. **Zero External Data:**
   - No Google Maps, MapMyIndia, OpenStreetMap, or Nominatim API calls.
   - No external web search or corporate registration scrapers.
   - All transliteration, tokenization, and normalization must execute offline and self-contained within Python.
2. **Physical Memory Ceiling (8 GB RAM):**
   - The execution hardware is standard consumer hardware (8 GB RAM).
   - In-memory materialization of all Cartesian pairs or massive sparse matrices causes immediate Out-Of-Memory (OOM) termination.
   - Candidate generation must run with streaming evaluation or chunked execution to keep peak memory below **1 GB**.
3. **Multilingual & Country Independence:**
   - Training data comprises United States (`US`) and India (`India`) records.
   - The test set introduces **France** (`France` / `FR`), featuring French legal forms (`SARL`, `SAS`, `EURL`, `SA`, `SCI`) and French address formatting.
   - The blocking architecture must not rely on US-only assumptions (such as 5-digit ZIP codes) and must handle diverse linguistic regimes gracefully.
4. **Target Exclusivity Invariant:**
   - In ground truth, every noisy target record in Source 2 or Source 3 matches **at most one** Source 1 entity.
   - True pairs are **100% intra-country** (zero cross-country matches exist in ground truth).
