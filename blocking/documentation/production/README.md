# Production Operations & Runbook Directory

This directory contains the operational architecture, execution runbooks, validation protocols, and data contracts for deploying the frozen **Champion v2 Surgical** candidate generator at scale.

---

## 1. Directory Structure

| File | Purpose |
|:---|:---|
| [`README.md`](README.md) | Navigation and overview of production operations. |
| [`FULL_SCALE_BLOCKING_PLAN.md`](FULL_SCALE_BLOCKING_PLAN.md) | Architectural plan for full-scale candidate generation (2.23M queries, 10.3M targets). |
| [`RUNBOOK.md`](RUNBOOK.md) | Step-by-step execution guide, CLI commands, hardware constraints, and troubleshooting. |
| [`VALIDATION_CHECKLIST.md`](VALIDATION_CHECKLIST.md) | Pre-flight and post-execution data integrity checklists and verification tests. |
| [`OUTPUT_CONTRACT.md`](OUTPUT_CONTRACT.md) | Formal interface specification defining the candidate output schema for Phase 3. |

---

## 2. Production Operating Parameters

- **Target Corpus**: 10,309,088 records (7.45M US, 2.86M India).
- **Query Corpus ($S1$)**: 2,233,142 records (1.52M US, 712k India).
- **Execution Architecture**: Inverted Hash Indexing with Streaming Micro-Batching (10,000 queries per batch).
- **Expected Total Candidate Pairs**: $\approx 2.55\text{ Billion Candidate Pairs}$ (streamed to disk/feature pipeline).
- **Memory Footprint**: Strict limit $\le 4.0\text{ GB}$ peak RAM.
- **Estimated Full Wall-Clock Time**: $\approx 20\text{ minutes}$ across country partitions.
