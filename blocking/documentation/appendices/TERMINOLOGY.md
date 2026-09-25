# Glossary of Entity Resolution & Blocking Terminology

This glossary defines standard terminology, acronyms, and project-specific concepts used throughout the codebase and documentation.

---

## 1. Dataset & Challenge Terminology

- **$S1$ (Query Entity)**: The primary query record representing a business entity that must be resolved against secondary corporate registries.
- **$S2$ / $S3$ (Target Records)**: Records in target registry datasets that represent candidate matches for $S1$ queries. $S2$ corresponds to primary registry listings; $S3$ corresponds to alternate/tax filings.
- **1-to-Many Cardinality ($1:k$)**: The property where a single $S1$ entity corresponds to multiple valid target records ($1 \le k \le 17$). In our benchmark, 10,000 $S1$ entities map to 34,481 target entities ($\mu = 3.45$ matches per query).
- **Distractor Record**: Target corpus records that do not match any query in the current benchmark, included to realistically simulate production search noise.
- **Country Partitioning**: The architectural rule enforcing that records in country $C$ are only blocked against targets in country $C$.

---

## 2. Blocking & Indexing Concepts

- **Candidate Generation (Blocking)**: The fast retrieval phase in entity resolution that reduces the $O(N \times M)$ search space to a manageable set of candidate pairs $O(N \times k)$ where $k \ll M$.
- **Inverted Index**: A hash table mapping indexing keys (e.g., words, prefixes, digits) to posting lists containing matching record IDs.
- **Posting List**: The array of record identifiers associated with a specific index key in an inverted index.
- **Composite Blocking Key**: A multi-attribute compound key formed by conjunction ($A \land B$), such as `(Name Token, Location Token)` or `(Prefix-4, Street Digit)`.
- **Channel**: A distinct feature extraction and indexing mechanism (e.g., Channel B = exact name, Channel C = significant tokens, Channel D = prefix-4, Channel E = digits, Channel F = location).
- **Core Backbone ($B+C+D+E$)**: The high-efficiency candidate generator combining exact names, significant name tokens, 4-char prefixes, and address digits.
- **Multi-Match Blindspot**: The structural failure mode occurring when a candidate generator skips fallback channels for a query because it already generated candidates ($k \ge 10$). In 1-to-many ER, this drops secondary targets.
- **Dynamic Rarity (Top-2 Rarest Indexing)**: Selecting the top-2 highest IDF (lowest corpus frequency) location tokens locally per target record, rather than dropping common tokens globally.
- **Surgical Tail Pipeline**: Four specialized micro-channels (2-char tokens, domain stems, consonant collapsing, and enriched digits + loc) engineered to recover hard-tail misses without candidate explosion.
- **Champion v1**: The 3-tier hierarchical architecture established in Experiment 06 (L1 Sieve + L2 Backbone + L3 5% IDF Filtered F).
- **Champion v2 Surgical**: The finalized, frozen candidate generator combining Champion v1, Top-2 location rarity, surgical tail channels, and micro-signals S2, S4, and S5.
- **Indic Transliteration**: Script conversion mapping Brahmic scripts (Devanagari, Bengali, Gujarati, Kannada, Tamil, Telugu, Malayalam, Gurmukhi, Oriya) into Romanized Latin text.
