# Biomedical NER Ensemble — Evaluation Report

**Project:** Bio-Semantic Parser  
**Evaluation Date:** July 2026  
**Notebooks:** `ner_benchmark_scispacy_hunflair2.ipynb` (F1 benchmark), `ner_benchmark_gliner_biomed.ipynb` (GLiNER benchmark), `ner_qualitative_pmc7390530_sirtuins.ipynb` (Qualitative Sirtuins), `ner_qualitative_pmc11975295_alzheimers.ipynb` (Qualitative Alzheimer's), `ner_qualitative_pmc8160999_natural_products.ipynb` (Qualitative Natural Products)

---

## 1. Overview

This report documents the full evaluation of the Bio-Semantic Parser's Named Entity Recognition (NER) ensemble. The evaluation combines:

1. **Quantitative benchmarks** — F1 scores measured against four established gold-standard datasets (BC5CDR, BioNLP2004/JNLPBA, BioNLP-13-CG).
2. **Qualitative analysis** — Per-sentence inspection across three real-world open-access biomedical articles from PubMed Central, covering distinct biomedical domains.

The goal was to determine how to best combine four models — `scispaCy bc5cdr`, `scispaCy jnlpba`, `scispaCy bionlp13cg`, and `HunFlair2` — into a single ensemble that maximizes precision and recall across a wide range of biomedical entity types.

---

## 2. Models Under Evaluation

| Model | Library | Entity Types Covered |
|---|---|---|
| `en_ner_bc5cdr_md` | scispaCy | DISEASE, CHEMICAL |
| `en_ner_jnlpba_md` | scispaCy | DNA, RNA, PROTEIN, CELL_TYPE, CELL_LINE |
| `en_ner_bionlp13cg_md` | scispaCy | GENE_OR_GENE_PRODUCT, CANCER, ORGANISM, TISSUE, ORGAN, CELL, CELLULAR_COMPONENT, SIMPLE_CHEMICAL, AMINO_ACID, PATHOLOGICAL_FORMATION |
| `HunFlair2` | Flair | Gene, Disease, Chemical, Species, CellLine |
| `GLiNER-BioMed` | GLiNER | Zero-shot: mutations, phenotypes, pathways, epigenomic features (gap filler) |

---

## 3. Quantitative Benchmarks (F1 Scores)

> **Source: `ner_benchmark_scispacy_hunflair2.ipynb`** — Each model evaluated against its respective gold-standard corpus on 200 examples (BC5CDR/JNLPBA) and 100 documents (BioNLP-13-CG).

### 3.1 BC5CDR — Disease & Chemical

Evaluated on `tner/bc5cdr` (200 examples).

| Model | Precision | Recall | Micro F1 |
|---|---|---|---|
| scispaCy bc5cdr | **0.878** | 0.823 | **0.850** |
| HunFlair2 | 0.854 | **0.841** | 0.848 |

**Key finding:** The two models are essentially tied overall. BC5CDR has marginally higher precision. HunFlair2 has marginally higher recall. On **Chemical** specifically, HunFlair2 is stronger (F1 0.880 vs 0.862). On **Disease**, BC5CDR is stronger (F1 0.834 vs 0.810).

### 3.2 BioNLP2004 / JNLPBA — Genes, Proteins, DNA, Cell Types

Evaluated on `tner/bionlp2004` (200 examples, approximate label mapping for HunFlair2).

| Model | DNA F1 | Protein F1 | Cell Type F1 | Cell Line F1 | **Micro F1** |
|---|---|---|---|---|---|
| scispaCy jnlpba | 0.728 | 0.691 | 0.649 | 0.613 | **0.684** |
| HunFlair2 | 0.000 | **0.576** | 0.000 | 0.043 | 0.380 |
| scispaCy bionlp13cg | 0.000 | 0.445 | 0.000 | 0.000 | 0.285 |

**Key finding:** JNLPBA dominates this benchmark. HunFlair2's structural label gaps (no DNA/RNA/CELL_TYPE category) and its catastrophically low CELL_LINE F1 (0.043) confirm two critical design decisions:
- **jnlpba must be the primary authority on DNA, RNA, PROTEIN, CELL_TYPE, CELL_LINE.**
- **HunFlair2's CellLine category should be actively discarded**, even though the label exists.

> **Important caveat:** This benchmark is not entirely "fair" to HunFlair2. The 0.380 micro-F1 largely reflects annotation-scheme mismatch (HunFlair2 predicts `Gene` where the gold labels it `DNA`), not genuine inability to detect the entities. The CELL_LINE F1 of 0.043, however, is a genuine weakness, confirmed qualitatively.

### 3.3 BioNLP-13-CG — Full Biomedical Ontology

Evaluated on `bigbio/bionlp_st_2013_cg` (100 documents). This is bionlp13cg's **own training domain**.

| Entity Type | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| Gene_or_gene_product | 0.933 | 0.884 | **0.907** | 1082 |
| Cell | 0.938 | 0.854 | **0.894** | 618 |
| Simple_chemical | 0.903 | 0.905 | **0.904** | 349 |
| Cancer | 0.849 | 0.854 | **0.851** | 349 |
| Tissue | 0.927 | 0.828 | **0.874** | 122 |
| Organ | 0.982 | 0.862 | **0.918** | 65 |
| Organism | 0.604 | 0.532 | 0.566 | 267 |
| Multi-tissue_structure | 0.000 | 0.000 | **0.000** | 184 |
| **Micro avg** | 0.887 | 0.787 | **0.834** | 3258 |

**Key finding:** bionlp13cg is very strong on its own domain. Its ORGAN, TISSUE, CELL, and CANCER categories are genuinely excellent. Its ORGANISM coverage (F1 0.566) is significantly weaker than HunFlair2's real-world species tagging, confirming the decision to strip its ORGANISM labels in the ensemble.

---

## 4. Qualitative Analysis — Three Real-World PMC Articles

> **Sources:** `ner_qualitative_pmc11975295_alzheimers.ipynb` (Report 1), `ner_qualitative_pmc7390530_sirtuins.ipynb` (Report 2), and `ner_qualitative_pmc8160999_natural_products.ipynb` (Report 3).

### 4.1 Report 1: PMC11975295 — Alzheimer's Disease (Clinical/Therapeutic)

**Domain:** Clinical neurology, drug names, patient treatments  
**Entity distribution:** Heavy on DISEASE and CHEMICAL, sparse on GENE/PROTEIN

| Model | Qualitative Assessment |
|---|---|
| BC5CDR | Excellent on standard diseases and drugs. **Misses newer biologics** (aducanumab, lecanemab, Donanemab) not in its training vocabulary. |
| HunFlair2 | **Best overall.** Catches all modern drug names BC5CDR misses. Correctly tags `ApoE4` → Gene and `ARIA-E` → Gene. |
| JNLPBA | Near useless for this domain — the text contains almost no genes or proteins. |
| bionlp13cg | High recall but **severe false positives**: `AD` → ORGANISM, `disease` → CANCER, `patients` → ORGANISM, `Cambridge` → ORGANISM. |

### 4.2 Report 2: PMC7390530 — Sirtuin Biology (Molecular)

**Domain:** Aging biology, gene regulation, molecular pathways  
**Entity distribution:** Rich in GENE/PROTEIN/DNA, some DISEASE and SPECIES

| Model | Qualitative Assessment |
|---|---|
| HunFlair2 | **Strongest overall.** Two standout advantages not measured by any F1 benchmark: **(a) Species tagging** — correctly identifies "yeast", "mice", "C. elegans", "fruit flies", "D. melanogaster" consistently. bionlp13cg tags "fly D." → CELL and "cerevisiae" → CELL. **(b) Span boundary quality** — in dense gene-list sentences (DAF-16, HSF-1, IGF-1), correctly splits adjacent genes; jnlpba merges them into garbled spans ("FOXO,4E-BP INR", "Mn-SOD Wnt"). |
| JNLPBA | Strong protein recall but **over-tags generic phrases**: "conserved recognition motif", "91-amino-acid segment", "60 core domains". |
| bionlp13cg | High recall, poor precision. Tags "Brain-specific" → Gene, "fly D." → CELL, "C." alone → ORGANISM. |
| BC5CDR | Very weak — the text contains almost no chemicals or diseases. Frequently returns 0 entities. |

### 4.3 Report 3: Multi-domain Biomedical Literature (Highest Complexity)

**Domain:** Natural products, nanotechnology, antimicrobial research, cancer cell lines  
**Entity distribution:** Widest variety — chemicals, diseases, organisms, cell lines, genes simultaneously

| Model | Qualitative Assessment |
|---|---|
| HunFlair2 | Most consistent across all domains. Adapts to clinical and molecular biology text alike. |
| BC5CDR | Good on disease/chemical-heavy passages. Limited beyond those categories. |
| JNLPBA | Moderate — finds genes/proteins but completely blind to chemicals and organisms. |
| bionlp13cg | Highest recall, but proportionally more false positives in this multi-domain setting. |

---

## 5. Cross-Domain Difficulty Ranking

| Aspect | Report 1 (Alzheimer's) | Report 2 (Sirtuins) | Report 3 (Multi-domain) |
|---|---|---|---|
| PMC ID | PMC11975295 | PMC7390530 | PMC8160999 |
| Domain | Clinical neurology | Aging/molecular biology | Natural products, cancer, nanotechnology |
| Dominant entities | Disease, Chemical | Gene, Protein, DNA, Species | All types simultaneously |
| Entity diversity | Low–Moderate | High | **Very High** |
| NER difficulty | Medium | High | **Highest** |

---

## 6. Final Design Decision: Label-Specific Authority Matrix

Based on combining the F1 benchmarks with qualitative span analysis, a simple "Model A always beats Model B" merge is insufficient. The ensemble uses a **4-Tier Label-Specific Authority Matrix** implemented in `src/preextraction/preextractor.py`.

Within each tier, spans are sorted **longest-first** to prevent short high-priority spans from blocking longer informative ones.

### Tier 1 — Absolute Authorities & Boundary Dictators

| Model | Label(s) | Rationale |
|---|---|---|
| `HunFlair2` | Species | Sole authority. bionlp13cg ORGANISM actively stripped. |
| `HunFlair2` | Chemical | Highest recall on modern drug names (F1 0.880). |
| `bc5cdr` | DISEASE | Highest precision on diseases (F1 0.834 vs 0.810). |
| `jnlpba` | CELL_LINE, CELL_TYPE | Clear authority. HunFlair2 CellLine (F1 = 0.043) actively dropped. |
| `HunFlair2` | Gene | **Span boundary tiebreaker.** Claims clean individual gene boundaries first; prevents jnlpba's garbled concatenated spans. |

### Tier 2 — Strong Backups & Coverage Fillers

| Model | Label(s) | Rationale |
|---|---|---|
| `jnlpba` | DNA, RNA, PROTEIN | Superior F1 (0.684). Garbled spans safely dropped if they overlap Tier 1 boundaries; novel entities fill the gap. |
| `HunFlair2` | Disease | Secondary — catches entities bc5cdr misses ("reactive gliosis", "β-amyloid plaques"). |
| `bc5cdr` | CHEMICAL | Secondary chemical backup. |

### Tier 3 — Structural & Ontology Fallbacks

| Model | Label(s) | Rationale |
|---|---|---|
| `bionlp13cg` | TISSUE, ORGAN, CANCER, CELL, CELLULAR_COMPONENT, etc. | Good F1 in own domain (0.834). **ORGANISM and GENE_OR_GENE_PRODUCT actively filtered** to prevent noise. |

### Tier 4 — Zero-Shot Gap Fillers

| Model | Label(s) | Rationale |
|---|---|---|
| `GLiNER-BioMed` | Genomic variant, phenotype, biological pathway, epigenomic feature, macromolecular complex | Covers entity types not present in any supervised model. |

---

## 7. Summary of Key Findings

1. **HunFlair2 is the most domain-agnostic model.** Its species tagging and span boundary quality are unique practical advantages not captured by any F1 benchmark.

2. **scispaCy jnlpba is the authoritative source for DNA/RNA/Protein/CellType.** Its F1 advantage (0.684 vs 0.380) and coverage of entity types HunFlair2 lacks entirely makes it irreplaceable for molecular biology text.

3. **scispaCy bionlp13cg is a high-recall, lower-precision model.** Excellent in its own domain (0.834 micro F1) and provides unique TISSUE/ORGAN/CANCER coverage, but its ORGANISM and GENE_OR_GENE_PRODUCT labels must be filtered in the ensemble to avoid noise.

4. **scispaCy bc5cdr is narrow but precise.** The most reliable source for DISEASE annotation (highest precision) and a useful backup for CHEMICAL.

6. **Simple sequential model priority is insufficient.** The final architecture routes every extracted entity through a label-specific tier, ensuring no model's weaknesses propagate to entity types where another model is objectively stronger.

---

## 8. Reproducibility

| Notebook | Purpose |
|---|---|
| `ner_benchmark_scispacy_hunflair2.ipynb` | F1 benchmarks: BC5CDR, BioNLP2004/JNLPBA, BioNLP-13-CG |
| `ner_benchmark_gliner_biomed.ipynb` | F1 benchmark: GLiNER-BioMed zero-shot |
| `ner_qualitative_pmc7390530_sirtuins.ipynb` | Qualitative comparison on PMC7390530 (Sirtuin biology) |
| `ner_qualitative_pmc11975295_alzheimers.ipynb` | Qualitative comparison on PMC11975295 (Alzheimer's disease) |
| `ner_qualitative_pmc8160999_natural_products.ipynb` | Qualitative comparison on PMC8160999 (Natural products/multi-domain) |
| `src/preextraction/preextractor.py` | Final production ensemble implementation |
