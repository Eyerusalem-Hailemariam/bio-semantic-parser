"""
Layer 4 — Pre-Extraction Orchestrator

Runs a 5-model hybrid NER ensemble (HunFlair2, scispaCy, GLiNER), 
applies PubTator3 normalization for PubMed articles, then classifies 
each entity's containing clause for negation.
"""
import spacy
from flair.nn import Classifier
from flair.data import Sentence
from gliner import GLiNER
from src.preextraction.ner_tagger import NERTagger
from src.preextraction.negation_detector import NegationDetector
from src.preextraction.doi_extractor import DOIExtractor
from src.preextraction.accession_detector import AccessionDetector
from src.preextraction.pubtator_client import fetch_pubtator_entities


class Preextractor:
    def __init__(self):
        self._nlp_bc5 = spacy.load("en_ner_bc5cdr_md")     # DISEASE, CHEMICAL
        self._nlp_jnl = spacy.load("en_ner_jnlpba_md")     # DNA, RNA, PROTEIN, CELL_TYPE, CELL_LINE
        self._nlp_bio = spacy.load("en_ner_bionlp13cg_md") # GENE_OR_GENE_PRODUCT, TISSUE, ORGAN, CANCER, CELLULAR_COMPONENT
        
        self._hunflair = Classifier.load('hunflair2')
        
       
        self._gliner_model = GLiNER.from_pretrained("Ihor/gliner-biomed-large-v1.0")
        self._gliner_labels = [
            "genomic variant", "sequence variant", "structural variant", "SNP", "mutation",
            "phenotype", "clinical symptom", 
            "biological pathway", "biochemical reaction", "biological process", "molecular function",
            "enhancer", "promoter", "binding motif", "epigenomic feature",
            "macromolecular complex", "experimental factor"
        ]
        self._gliner_threshold = 0.3

        self.negation_detector  = NegationDetector()
        self.doi_extractor      = DOIExtractor()
        self.accession_detector = AccessionDetector()

    def _run_ensemble(self, text: str):
        sentence = Sentence(text)
        self._hunflair.predict(sentence)
        
        doc_bc5 = self._nlp_bc5(text)
        doc_jnl = self._nlp_jnl(text)
        doc_bio = self._nlp_bio(text)
        
        gliner_entities = self._gliner_model.predict_entities(
            text, 
            self._gliner_labels, 
            threshold=self._gliner_threshold
        )

        tier1, tier2, tier3, tier4 = [], [], [], []

        for span in sentence.get_spans('ner'):
            s = (span.start_position, span.end_position, span.tag)
            if span.tag in ["Species", "Chemical", "Gene"]:
                tier1.append(s)
            elif span.tag == "Disease":
                tier2.append(s)

        for e in doc_bc5.ents:
            s = (e.start_char, e.end_char, e.label_)
            if e.label_ == "DISEASE":
                tier1.append(s)
            elif e.label_ == "CHEMICAL":
                tier2.append(s)

        for e in doc_jnl.ents:
            s = (e.start_char, e.end_char, e.label_)
            if e.label_ in ["CELL_LINE", "CELL_TYPE"]:
                tier1.append(s)
            elif e.label_ in ["DNA", "RNA", "PROTEIN"]:
                tier2.append(s)

        for e in doc_bio.ents:
            if e.label_ not in ["ORGANISM", "GENE_OR_GENE_PRODUCT"]:
                tier3.append((e.start_char, e.end_char, e.label_))

        for e in gliner_entities:
            tier4.append((e['start'], e['end'], e['label']))

        occupied: list[tuple[int, int]] = []
        merged_spans = []

        def _overlaps(start: int, end: int) -> bool:
            return any(start < b_end and b_start < end for b_start, b_end in occupied)

        def add_spans(spans):
            # Sort longest span first within this priority tier
            for start, end, label in sorted(spans, key=lambda s: s[1] - s[0], reverse=True):
                if not _overlaps(start, end):
                    merged_spans.append((start, end, label))
                    occupied.append((start, end))

        add_spans(tier1)
        add_spans(tier2)
        add_spans(tier3)
        add_spans(tier4)

        final_doc = self._nlp_bio(text)
        final_ents = []
        for start, end, label in merged_spans:
            span = final_doc.char_span(start, end, label=label, alignment_mode="expand")
            if span is not None:
                final_ents.append(span)

        final_doc.ents = spacy.util.filter_spans(final_ents)
        return final_doc

    def process(self, chunk: dict) -> dict:
        text     = chunk["text"]
        doc      = self._run_ensemble(text)
        entities = NERTagger.from_doc(doc)

        doc_id      = chunk.get("document_id", "")
        source_name = chunk.get("source_name", "")

        if source_name == "pubmed" and doc_id and len(doc_id) <= 10:
            pt_entities = fetch_pubtator_entities(doc_id)
            if pt_entities:
                entities = _merge_entities(entities, pt_entities)

        negation    = self.negation_detector.process(entities, doc)
        doi         = self.doi_extractor.extract(text)
        accessions  = self.accession_detector.extract(text)

        original_pdf_hash = doc_id if len(doc_id) == 64 else None
        if doi and len(doc_id) == 64:
            doc_id = doi

        return {
            **chunk,
            "document_id":       doc_id,
            "original_pdf_hash": original_pdf_hash,
            "entities":          negation["entities"],
            "has_negation":      negation["has_negation"],
            "negated_entities":  negation["negated_entities"],
            "doi":               doi,
            "accession_numbers": accessions,
        }

    def process_batch(self, chunks: list) -> list:
        return [self.process(chunk) for chunk in chunks]


def _merge_entities(ensemble: list, pubtator: list) -> list:
    """PubTator3 entities (with normalization IDs) take priority; ensemble fills gaps."""
    pt_normalized = {e["normalized"] for e in pubtator}
    gap_fillers   = [e for e in ensemble if e["normalized"] not in pt_normalized]
    return pubtator + gap_fillers
