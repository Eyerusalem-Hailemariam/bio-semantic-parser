"""
Component 1 — Relationship Taxonomy
────────────────────────────────────
Single source of truth for all biological relation types used in extraction.

Sources (5 schemas — all aligned to 100% coverage)
────────────────────────────────────────────────────
  • BioNLP Shared Tasks          — gene/protein event ontology (GE, EPI, BB tasks)
                                   https://sites.google.com/site/bionlpst/
                                   Paper: https://aclanthology.org/W11-1801
  • Hetionet v1.0                — network medicine metaedge types
                                   https://het.io/ | https://github.com/hetio/hetionet
                                   Paper: https://elifesciences.org/articles/26726
  • OpenBioLink                  — large-scale KG benchmark edge types
                                   https://github.com/OpenBioLink/OpenBioLink
                                   Paper: https://doi.org/10.1093/bioinformatics/btaa274
  • BioCypher primer schema      — node types + regulatory/genomic/ontology edges
                                   https://biocypher.org/ | https://github.com/biocypher/biocypher
                                   Paper: https://doi.org/10.1038/s41587-023-01848-y
  • Biolink Model v4.4.2         — standard biological predicate ontology (100% mapped)
                                   https://biolink.github.io/biolink-model/
                                   https://github.com/biolink/biolink-model

When different schemas refer to the same biological concept using different
names, ONE canonical English verb is chosen here and all aliases are recorded
in SYNONYM_MAP below. This prevents the same relationship from being stored
under multiple labels in the knowledge graph.

File structure (8 sections)
────────────────────────────
  1. RelationType enum     — 87 approved types organised into 22 categories
  2. EntityType enum       — 39 node types (BioCypher + Biolink aligned)
  3. SectionLabel enum     — document section tags
  4. TAXONOMY dict         — definition + example + not_this for every type
  5. SYNONYM_MAP           — empty stub (moved to tools/build_taxonomy.py)
  6. CROSS_SCHEMA_MAP      — canonical → equivalent name in each source schema
  7. BIOLINK_MAPPING       — canonical → biolink predicate (used by Layer 7)
  8. OPPOSING_RELATIONS    — contradiction pairs (used by Layer 7)

Note on SYNONYM_MAP
───────────────────
The synonym map was an offline audit lookup used only by tools/build_taxonomy.py
to check coverage against external schemas. It is NOT used at runtime — the LLM
normalises predicates directly from the closed taxonomy in the extraction prompt.
Hardcoding synonyms in the runtime schema is the wrong approach for scale; the
correct approach is embedding-based semantic matching if ever needed at runtime.

Growth policy
─────────────
This is a static closed enum — updated offline, not at runtime.
When the extraction engine encounters a relation that fits no type here,
the chunk is routed to the human review queue. A new type is added only
after domain-expert approval and ≥ 3 independent paper occurrences.
"""
from enum import Enum
from typing import Dict


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Relation types and categories
# ══════════════════════════════════════════════════════════════════════════════

class RelationType(str, Enum):

    # ── Category 1: Gene / RNA Expression ─────────────────────────────────────
    # BioNLP: Gene_expression, Transcription, Translation
    # Hetionet: AeG (Anatomy-expresses-Gene)
    # OpenBioLink: GENE_ANATOMY expressed_in
    EXPRESSED_IN     = "expressed_in"       # gene/protein detected in tissue or cell type
    TRANSCRIBES_TO   = "transcribes_to"     # DNA/gene → RNA product
    TRANSLATES_TO    = "translates_to"      # mRNA → protein product

    # ── Category 2: Activity Regulation ───────────────────────────────────────
    # BioNLP: Positive_regulation, Negative_regulation, Regulation
    # Hetionet: upregulates (AuG,CuG,DuG), downregulates (AdG,CdG,DdG), GrG
    ACTIVATES        = "activates"          # increases activity/function of a molecule
    INHIBITS         = "inhibits"           # decreases activity/function of a molecule
    UPREGULATES      = "upregulates"        # increases mRNA or protein abundance
    DOWNREGULATES    = "downregulates"      # decreases mRNA or protein abundance
    REGULATES        = "regulates"          # direction unspecified or bidirectional

    # ── Category 3: Post-Translational Modifications (PTMs) ───────────────────
    # BioNLP EPI task: Phosphorylation, Dephosphorylation, Methylation,
    #   Acetylation, Deacetylation, Ubiquitination, Deubiquitination,
    #   Sumoylation, Desumoylation, Hydroxylation, Dehydroxylation,
    #   Glycosylation, Deglycosylation, Neddylation, Deneddylation
    PHOSPHORYLATES   = "phosphorylates"     # kinase adds phosphate group
    DEPHOSPHORYLATES = "dephosphorylates"   # phosphatase removes phosphate group
    METHYLATES       = "methylates"         # methyltransferase adds methyl group
    DEMETHYLATES     = "demethylates"       # demethylase removes methyl group (DNA or protein)
    ACETYLATES       = "acetylates"         # acetyltransferase adds acetyl group
    DEACETYLATES     = "deacetylates"       # deacetylase (sirtuin/HDAC) removes acetyl group
    UBIQUITINATES    = "ubiquitinates"      # E3 ligase adds ubiquitin tag
    DEUBIQUITINATES  = "deubiquitinates"    # deubiquitinase (DUB) removes ubiquitin tag
    SUMOYLATES       = "sumoylates"         # SUMO ligase adds SUMO modifier
    DESUMOYLATES     = "desumoylates"       # SUMO protease removes SUMO modifier
    HYDROXYLATES     = "hydroxylates"       # hydroxylase adds hydroxyl group
    DEHYDROXYLATES   = "dehydroxylates"     # removes hydroxyl group
    GLYCOSYLATES     = "glycosylates"       # adds sugar moiety (O-GlcNAc, N-glycan)
    DEGLYCOSYLATES   = "deglycosylates"     # removes glycan / sugar moiety
    NEDDYLATES       = "neddylates"         # NEDD8 E3 ligase adds NEDD8 modifier
    DENEDDYLATES     = "deneddylates"       # deneddylase removes NEDD8 modifier

    # ── Category 4: Molecular Interactions ────────────────────────────────────
    # BioNLP: Binding
    # Hetionet: CbG (Compound-binds-Gene), GiG (Gene-interacts-Gene)
    # OpenBioLink: GENE_GENE interacts, GENE_DRUG targeted_by
    BINDS_TO         = "binds_to"           # direct demonstrated molecular binding
    INTERACTS_WITH   = "interacts_with"     # functional/genetic interaction, binding not proven
    IS_TARGET_OF     = "is_target_of"       # gene/protein is validated pharmacological target of drug

    # ── Category 5: Localisation, Transport & Secretion ──────────────────────
    # BioNLP: Localization, Transport
    # Hetionet: DlA (Disease-localizes-Anatomy)
    LOCALIZES_TO     = "localizes_to"       # protein found in or translocates to compartment/location
    TRANSPORTS       = "transports"         # active shuttling of molecule between compartments
    SECRETES         = "secretes"           # cell/organelle releases molecule into extracellular space

    # ── Category 6: Metabolic, Structural & Process Membership ────────────────
    # BioNLP: Conversion, Protein_catabolism, Protein_processing
    # Hetionet: GpPW/GpBP/GpCC/GpMF, PCiC (Pharmacologic Class-includes-Compound)
    # OpenBioLink: GENE_CATALYSIS_GENE, DRUG_CATALYSIS_GENE, participates_in (GO), ANATOMY_ANATOMY part_of
    # Biolink: catalyzes (is_a: participates in)
    CONVERTS_TO      = "converts_to"        # enzymatic transformation of A into distinct product B
    CLEAVES          = "cleaves"            # proteolytic cleavage of B by protease A
    CATALYZES        = "catalyzes"          # enzyme A catalyzes biochemical reaction or process B
    DEGRADES         = "degrades"           # proteolysis / autophagy / catabolism of B
    PARTICIPATES_IN  = "participates_in"    # gene/protein/compound is member of pathway or process
    PART_OF          = "part_of"            # A is a structural physical subunit or component of B
    IS_MEMBER_OF     = "is_member_of"       # compound/entity belongs to class or pharmacological family

    # ── Category 7: Causal / Mechanistic ──────────────────────────────────────
    CAUSES           = "causes"             # A is direct sufficient cause of B (experimentally proven)
    PROMOTES         = "promotes"           # A facilitates / accelerates B without direct causation
    PREVENTS         = "prevents"           # A blocks / suppresses occurrence of B

    # ── Category 8: Clinical / Therapeutic ────────────────────────────────────
    # Hetionet: CtD (Compound-treats-Disease), CpD (Compound-palliates-Disease)
    # OpenBioLink: indicated_for, biomarker_for
    TREATS           = "treats"             # intervention resolves or reverses disease B
    PALLIATES        = "palliates"          # intervention reduces severity without curing B
    BIOMARKER_FOR    = "biomarker_for"      # A indicates presence/risk/stage of condition B

    # ── Category 9: Statistical / Epidemiological ─────────────────────────────
    # Hetionet: DaG (associates), GcG (covaries), DrD/CrC (resembles)
    # OpenBioLink: associated_with (DisGeNET/OMIM)
    # Biolink: coexpressed with (is_a: correlated with); is missense/frameshift/splice variant of
    ASSOCIATES_WITH  = "associates_with"    # co-occurrence / genetic link, no established causality
    CORRELATES_WITH  = "correlates_with"    # statistical co-variation across samples or conditions
    COEXPRESSED_WITH = "coexpressed_with"   # genes show correlated expression across tissues/conditions
    RESEMBLES        = "resembles"          # structural/functional/phenotypic similarity
    PREDICTS         = "predicts"           # A forecasts future outcome B (prognostic)
    IS_VARIANT_OF    = "is_variant_of"      # genomic variant A is a variant of gene/sequence B

    # ── Category 10: Disease / Phenotype ──────────────────────────────────────
    # Hetionet: DpS (Disease-presents-Symptom)
    # OpenBioLink: DISEASE_PHENOTYPE, GENE_PHENOTYPE
    HAS_SYMPTOM      = "has_symptom"        # disease clinically presents with symptom B
    HAS_PHENOTYPE    = "has_phenotype"      # gene/variant/intervention produces phenotype B

    # ── Category 11: Longevity-Specific (domain extension) ────────────────────
    # Not present in BioNLP / Hetionet / OpenBioLink — added for longevity domain.
    # Sources:
    #   - DrugAge: curated assays with lifespan change (%) and increasing/decreasing outcomes
    #     https://genomics.senescence.info/drugs/
    #   - WHO HALE / healthy ageing: healthy years and functional ability are distinct from lifespan
    #     https://www.who.int/data/gho/indicator-metadata-registry/imr-details/7752
    #     https://www.who.int/news-room/questions-and-answers/item/healthy-ageing-and-functional-ability
    #   - GO:0043697 cell dedifferentiation + partial reprogramming aging literature
    #     https://www.ebi.ac.uk/QuickGO/term/GO:0043697
    #     https://doi.org/10.1016/j.cell.2016.11.052
    EXTENDS_LIFESPAN    = "extends_lifespan"    # intervention/gene increases measured total lifespan
    REDUCES_LIFESPAN    = "reduces_lifespan"    # mutation/compound decreases measured total lifespan
    EXTENDS_HEALTHSPAN  = "extends_healthspan"  # prolongs healthy disease-free period without necessarily total lifespan
    REDUCES_HEALTHSPAN  = "reduces_healthspan"  # shortens healthy functional period, accelerating age-related decline
    REPROGRAMS          = "reprograms"          # resets epigenetic/developmental state to younger or pluripotent identity

    # ── Category 12: Infection / Microbiology ─────────────────────────────────
    # BioNLP ID 2011 task: Infection, Immune_response
    INFECTS          = "infects"            # pathogen A infects / colonises host B

    # ── Category 13: Homology (BioCypher orthology/paralogy associations) ──────
    # BioCypher: orthology_association (DIOPT score), paralogy_association
    ORTHOLOG_OF      = "ortholog_of"        # gene X is ortholog of gene Y (speciation event)
    PARALOG_OF       = "paralog_of"         # gene X is paralog of gene Y (duplication event)

    # ── Category 14: Ontology hierarchy (BioCypher subclass_of / part_of) ─────
    # BioCypher: do_subclass_of, cl_subclass_of, hpo_subclass_of, etc.
    SUBCLASS_OF      = "subclass_of"        # term X is a subtype/subclass of term Y
    HAS_PART         = "has_part"           # X has Y as a component part

    # ── Category 15: Regulatory genomics (BioCypher regulatory_association) ───
    # BioCypher: non-coding elements regulating gene expression
    REGULATES_EXPRESSION_OF = "regulates_expression_of"  # regulatory element controls gene expression
    TARGETS                 = "targets"                  # TF / regulatory factor targets gene/region
    OPEN_CHROMATIN_AT       = "open_chromatin_at"        # chromatin accessible at this genomic region

    # ── Category 16: Genomic overlap (BioCypher structural variant associations) ─
    # BioCypher: feature_overlaps_structural_variant, gene_overlaps_structural_variant, etc.
    OVERLAPS                = "overlaps"                 # genomic feature A overlaps feature B by chromosomal coordinate

    # ── Category 17: Capability (BioCypher cl_capable_of) ─────────────────────
    # BioCypher: cl_capable_of (cell type → biological process)
    CAPABLE_OF              = "capable_of"               # entity (cell type, organism) is capable of performing process

    # ── Category 18: GO/RO molecular function relations (Biolink) ──────────────
    # biolink:enables, biolink:acts_upstream_of, biolink:contributes_to, biolink:occurs_in
    ENABLES                       = "enables"                       # gene product enables a molecular function/activity (GO:enables)
    ACTS_UPSTREAM_OF              = "acts_upstream_of"              # gene product is causally upstream of a biological process (RO:0002263)
    CONTRIBUTES_TO                = "contributes_to"                # gene/variant partially contributes to disease or process onset
    OCCURS_IN                     = "occurs_in"                     # biological process/event occurs in anatomical entity or cell type

    # ── Category 19: Developmental lineage (Biolink) ───────────────────────────
    # biolink:develops_from, biolink:derives_from
    DEVELOPS_FROM                 = "develops_from"                 # cell type / tissue develops from a precursor entity (RO:0002202)
    DERIVES_FROM                  = "derives_from"                  # entity is derived/produced from another entity (metabolite, product)

    # ── Category 20: Substrate / co-localisation (Biolink) ─────────────────────
    # biolink:has_substrate, biolink:colocalizes_with
    HAS_SUBSTRATE                 = "has_substrate"                 # enzyme or reaction has this molecule as substrate
    COLOCALIZES_WITH              = "colocalizes_with"              # two entities found in the same cellular/tissue location

    # ── Category 21: Clinical / pharmacological (Biolink) ──────────────────────
    # biolink:diagnoses, biolink:contraindicated_in, biolink:in_clinical_trials_for
    DIAGNOSES                     = "diagnoses"                     # clinical test / biomarker diagnoses a disease or condition
    CONTRAINDICATED_IN            = "contraindicated_in"            # drug/treatment is contraindicated in a disease or patient group
    IN_CLINICAL_TRIALS_FOR        = "in_clinical_trials_for"        # drug/intervention is currently in clinical trials for a disease

    # ── Category 22: Biolink completeness additions ─────────────────────────────
    # Inverse transcript/protein relations, complex membership, metabolite,
    # genetic/pharmacological interaction, temporal, amelioration, exacerbation, taxon
    TRANSCRIBED_FROM              = "transcribed_from"              # transcript is transcribed from gene (biolink:transcribed_from / RO:0002511)
    TRANSLATION_OF                = "translation_of"                # protein is the translation of transcript (biolink:translation_of)
    IN_COMPLEX_WITH               = "in_complex_with"               # two entities are subunits of the same molecular complex
    HAS_METABOLITE                = "has_metabolite"                # reaction / enzyme / pathway has this molecule as a metabolite product
    GENETICALLY_INTERACTS_WITH    = "genetically_interacts_with"    # genetic interaction — epistasis, synthetic lethality, suppression
    PHARMACOLOGICALLY_INTERACTS_WITH = "pharmacologically_interacts_with"  # drug–drug or drug–target pharmacological interaction
    PRECEDES                      = "precedes"                      # event / process A occurs before event / process B in time
    AMELIORATES                   = "ameliorates"                   # treatment / gene mitigates severity without curing (weaker than treats)
    EXACERBATES                   = "exacerbates"                   # gene / compound worsens or accelerates a disease or condition
    IN_TAXON                      = "in_taxon"                      # biological entity belongs to / is found in this organism taxon


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Entity types (mirror BioCypher schema node types)
# ══════════════════════════════════════════════════════════════════════════════

class EntityType(str, Enum):
    # ── Coding / sequence elements ────────────────────────────────────────────
    GENE                        = "GENE"                        # Ensembl / NCBI Gene ID
    PROTEIN                     = "PROTEIN"                     # UniProt accession
    TRANSCRIPT                  = "TRANSCRIPT"                  # Ensembl transcript ID
    EXON                        = "EXON"                        # Exon within a transcript
    NON_CODING_RNA              = "NON_CODING_RNA"              # miRNA, lncRNA, circRNA, piRNA

    # ── Genomic variation ─────────────────────────────────────────────────────
    GENOMIC_VARIANT             = "GENOMIC_VARIANT"             # rsID / SNP / small sequence variant
    SEQUENCE_VARIANT            = "SEQUENCE_VARIANT"            # specific DNA sequence alteration (ClinVar)
    STRUCTURAL_VARIANT          = "STRUCTURAL_VARIANT"          # large-scale rearrangement: CNV, SV, indel >50bp

    # ── Regulatory & epigenomic elements ─────────────────────────────────────
    REGULATORY_REGION           = "REGULATORY_REGION"           # general regulatory region
    ENHANCER                    = "ENHANCER"                    # enhancer element
    SUPER_ENHANCER              = "SUPER_ENHANCER"              # cluster of enhancers with high TF occupancy
    PROMOTER                    = "PROMOTER"                    # promoter region
    TRANSCRIPTION_FACTOR_BINDING_SITE = "TRANSCRIPTION_FACTOR_BINDING_SITE"  # TFBS
    EPIGENOMIC_FEATURE          = "EPIGENOMIC_FEATURE"          # epigenetic modification region
    MOTIF                       = "MOTIF"                       # TF binding motif (PWM)
    TAD                         = "TAD"                         # Topologically Associating Domain (Hi-C)

    # ── Chemistry & molecules ─────────────────────────────────────────────────
    SMALL_MOLECULE              = "SMALL_MOLECULE"              # ChEBI (drugs, metabolites, compounds)
    MOLECULAR_INTERACTION       = "MOLECULAR_INTERACTION"       # documented molecular interaction complex (IntAct/BioGRID)
    MACROMOLECULAR_COMPLEX      = "MACROMOLECULAR_COMPLEX"      # stable protein/nucleic acid complex (e.g. PRC2, ribosome)

    # ── Genetic composition ───────────────────────────────────────────────────
    HAPLOTYPE                   = "HAPLOTYPE"                   # set of co-inherited alleles on one chromosome
    GENOTYPE                    = "GENOTYPE"                    # full genetic makeup of an individual or strain

    # ── Disease & phenotype ───────────────────────────────────────────────────
    DISEASE                     = "DISEASE"                     # MeSH:D… / OMIM / DOID
    CANCER                      = "CANCER"                      # cancer subtype (MeSH:D…)
    PHENOTYPE                   = "PHENOTYPE"                   # HPO term
    SYMPTOM                     = "SYMPTOM"                     # clinical symptom (HPO / MeSH)

    # ── Biological processes & functions ─────────────────────────────────────
    PATHWAY                     = "PATHWAY"                     # Reactome / KEGG pathway ID
    REACTION                    = "REACTION"                    # Reactome biochemical reaction
    BIOLOGICAL_PROCESS          = "BIOLOGICAL_PROCESS"          # GO:XXXXXXX (BP)
    MOLECULAR_FUNCTION          = "MOLECULAR_FUNCTION"          # GO:XXXXXXX (MF)
    CELLULAR_COMPONENT          = "CELLULAR_COMPONENT"          # GO:XXXXXXX (CC)

    # ── Anatomy & cell biology ────────────────────────────────────────────────
    ANATOMY                     = "ANATOMY"                     # UBERON anatomical entity
    TISSUE                      = "TISSUE"                      # BTO tissue term
    CELL_TYPE                   = "CELL_TYPE"                   # CL cell ontology term
    CELL_LINE                   = "CELL_LINE"                   # CLO cell line
    DEVELOPMENTAL_STAGE         = "DEVELOPMENTAL_STAGE"         # HsapDv / developmental life stage

    # ── Experimental context ──────────────────────────────────────────────────
    EXPERIMENTAL_FACTOR         = "EXPERIMENTAL_FACTOR"         # EFO-derived experimental condition / treatment variable
    THREE_D_GENOME_STRUCTURE    = "THREE_D_GENOME_STRUCTURE"    # 3D chromatin organisation feature (Hi-C compartment/loop)

    # ── Taxonomy ──────────────────────────────────────────────────────────────
    ORGANISM                    = "ORGANISM"                    # NCBI Taxonomy ID

    # ── Catch-all ─────────────────────────────────────────────────────────────
    OTHER                       = "OTHER"                       # does not fit above — flag for review


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Section labels
# ══════════════════════════════════════════════════════════════════════════════

class SectionLabel(str, Enum):
    ABSTRACT      = "abstract"
    INTRODUCTION  = "introduction"
    METHODS       = "methods"
    RESULTS       = "results"
    DISCUSSION    = "discussion"
    SUPPLEMENTARY = "supplementary"
    UNKNOWN       = "unknown"


# ══════════════════════════════════════════════════════════════════════════════
